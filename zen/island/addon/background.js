// Panacea for Zen: answers the island (through the native host panacea_zen):
//   suggest {q}           -> {items: [{type: search|url|tab|bookmark|history|suggestion, ...}]}
//   open {text, newTab}   -> opens an address or searches with your default engine
//   switch {tabId}        -> selects that tab and its window
//   current               -> the active tab {title, url}
// Plain code, no AI. Only search suggestions leave the machine (to your search engine).
let port = null;

function connect() {
  port = browser.runtime.connectNative("panacea_zen");
  port.onMessage.addListener(async (m) => {
    let r;
    try { r = await handle(m); } catch (e) { r = { error: String(e) }; }
    port.postMessage({ id: m.id, ...r });
  });
  port.onDisconnect.addListener(() => { port = null; setTimeout(connect, 3000); });
}
connect();

const looksLikeUrl = (t) =>
  /^[a-z][a-z0-9+.-]*:\/\//i.test(t) || /^(about|file):/i.test(t) ||
  (!/\s/.test(t) && /^[^\s/]+\.[a-z]{2,}(:\d+)?(\/.*)?$/i.test(t)) || /^localhost(:\d+)?(\/|$)/i.test(t);
const toUrl = (t) => (/^[a-z][a-z0-9+.-]*:/i.test(t) ? t : "https://" + t);
const host = (u) => { try { return new URL(u).host; } catch { return ""; } };

async function engineSuggest(q) {
  const engine = (await browser.search.get()).find((e) => e.isDefault)?.name || "";
  let url = null;
  if (/duckduckgo/i.test(engine)) url = `https://duckduckgo.com/ac/?q=${encodeURIComponent(q)}&type=list`;
  else if (/google/i.test(engine)) url = `https://suggestqueries.google.com/complete/search?client=firefox&q=${encodeURIComponent(q)}`;
  if (!url) return { engine, list: [] };
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 1200);
  try {
    const res = await fetch(url, { signal: ctl.signal, credentials: "omit" });
    const data = await res.json();
    return { engine, list: (data[1] || []).filter((s) => s.toLowerCase() !== q.toLowerCase()).slice(0, 4) };
  } catch { return { engine, list: [] }; } finally { clearTimeout(t); }
}

async function suggest(q) {
  q = (q || "").trim();
  const ql = q.toLowerCase();
  const allTabs = (await browser.tabs.query({})).filter((t) => !t.incognito && /^(https?|about|file):/.test(t.url || ""));
  if (!q) {   // nothing typed: your most recent tabs
    return { items: allTabs.sort((a, b) => b.lastAccessed - a.lastAccessed).slice(0, 6)
      .map((t) => ({ type: "tab", tabId: t.id, title: t.title, url: t.url, host: host(t.url) })) };
  }
  const items = [];
  const seen = new Set();
  const add = (it) => { if (it.url && seen.has(it.url)) return; if (it.url) seen.add(it.url); items.push(it); };

  const [hist, books, sugg] = await Promise.all([
    browser.history.search({ text: q, maxResults: 30, startTime: 0 }),
    browser.bookmarks.search(q).catch(() => []),
    engineSuggest(q),
  ]);
  if (looksLikeUrl(q)) add({ type: "url", url: toUrl(q), title: q, host: host(toUrl(q)) });
  else items.push({ type: "search", text: q, engine: sugg.engine });

  allTabs.filter((t) => (t.title || "").toLowerCase().includes(ql) || (t.url || "").toLowerCase().includes(ql))
    .slice(0, 3).forEach((t) => add({ type: "tab", tabId: t.id, title: t.title, url: t.url, host: host(t.url) }));
  books.filter((b) => b.url).slice(0, 2)
    .forEach((b) => add({ type: "bookmark", title: b.title, url: b.url, host: host(b.url) }));
  hist.sort((a, b) => (b.visitCount || 0) - (a.visitCount || 0) || (b.lastVisitTime || 0) - (a.lastVisitTime || 0))
    .slice(0, 5).forEach((h) => add({ type: "history", title: h.title || h.url, url: h.url, host: host(h.url) }));
  sugg.list.forEach((s) => items.push({ type: "suggestion", text: s, engine: sugg.engine }));
  return { items: items.slice(0, 12) };
}

async function activeTab() {
  const [t] = await browser.tabs.query({ active: true, lastFocusedWindow: true });
  return t;
}

async function handle(m) {
  switch (m.cmd) {
    case "suggest": return suggest(m.q);
    case "current": { const t = await activeTab(); return t ? { title: t.title, url: t.url, host: host(t.url) } : {}; }
    case "switch": {
      const t = await browser.tabs.update(Number(m.tabId), { active: true });
      await browser.windows.update(t.windowId, { focused: true }).catch(() => {});
      return { ok: true };
    }
    case "open": {
      const text = String(m.text || "").trim();
      if (!text) return { error: "empty" };
      const cur = await activeTab();
      if (looksLikeUrl(text)) {
        const url = toUrl(text);
        if (m.newTab || !cur) await browser.tabs.create({ url });
        else await browser.tabs.update(cur.id, { url });
      } else {
        await browser.search.search({ query: text, disposition: m.newTab || !cur ? "NEW_TAB" : "CURRENT_TAB" });
      }
      return { ok: true };
    }
    case "ping": return { pong: true };
    default: return { error: "unknown command" };
  }
}
