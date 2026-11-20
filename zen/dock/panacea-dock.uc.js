// ==UserScript==
// @name        Panacea dock
// @description Loads chrome/panacea-dock.css (the bottom url-bar dock layout) while the
//              pref panacea.zen.dock is true, and reloads it live when the file changes.
// ==/UserScript==
// Part of panacea-config (zen/dock). Turn the layout off: about:config, panacea.zen.dock = false.
// Address-bar mode: about:config, panacea.zen.urlbar = "dock" (default: the bottom dock, and the
// island is the bar only while Zen is alone on its screen) or "island" (the dock always hidden;
// the island is the bar whenever Zen has focus). Switches live.
(function () {
  const PREF = "panacea.zen.dock";
  const FILE = PathUtils.join(PathUtils.profileDir, "chrome", "panacea-dock.css");
  const wu = window.windowUtils;
  let loaded = null, mtime = 0, timer = null;

  if (!Services.prefs.prefHasUserValue(PREF)) Services.prefs.setBoolPref(PREF, true);

  function unload() {
    if (loaded) { try { wu.removeSheetUsingURIString(loaded, wu.USER_SHEET); } catch (e) {} loaded = null; }
    document.documentElement.removeAttribute("panacea-dock");
  }
  async function refresh(force) {
    if (!Services.prefs.getBoolPref(PREF, true)) { unload(); return; }
    let st;
    try { st = await IOUtils.stat(FILE); } catch (e) { unload(); return; }
    if (!force && loaded && st.lastModified === mtime) return;
    mtime = st.lastModified;
    const uri = PathUtils.toFileURI(FILE) + "?v=" + mtime;
    unload();
    wu.loadSheetUsingURIString(uri, wu.USER_SHEET);
    loaded = uri;
    document.documentElement.setAttribute("panacea-dock", "true");
  }
  const observer = { observe: () => refresh(true) };
  Services.prefs.addObserver(PREF, observer);
  timer = setInterval(() => refresh(false), 1000);   // live reload while editing
  window.addEventListener("unload", () => { clearInterval(timer); Services.prefs.removeObserver(PREF, observer); }, { once: true });
  refresh(true);

  // ------------------------------------------------------------ panels open upward
  // Panels anchored in the dock (site info, permissions, add-on install prompts,
  // extension buttons...) normally open downward: off-screen at the bottom.
  // Flip every one of them above its anchor while the dock is on.
  const flip = (pos) => {
    if (!pos) return "topcenter bottomleft";
    if (pos.startsWith("after_")) return pos.replace("after_", "before_");
    const m = pos.match(/^(top|bottom)(\S*)\s+(top|bottom)(\S*)$/);
    if (m && m[1] === "bottom") return `top${m[2]} bottom${m[4]}`;
    return pos;
  };
  const inDock = (a) => document.documentElement.hasAttribute("panacea-dock") &&
    a && a.closest && a.closest("#urlbar-container, #urlbar, #notification-popup-box");
  const origOpen = XULPopupElement.prototype.openPopup;
  XULPopupElement.prototype.openPopup = function (anchor, opts, ...rest) {
    try {
      if (inDock(anchor)) {
        if (opts && typeof opts === "object") opts = { ...opts, position: flip(opts.position || this.getAttribute("position")) };
        else opts = flip(opts || this.getAttribute("position"));
      }
    } catch (e) {}
    return origOpen.call(this, anchor, opts, ...rest);
  };

  // ------------------------------------------------------------ the pill's width
  // Fits the text (address, what you type, or the placeholder); CSS animates it
  // (width: var(--dock-w), the island's ease), since width:auto can't animate.
  const ctx = document.createElement("canvas").getContext("2d");
  let label = null;
  // idle: the site's domain only (youtube.com); focused: the full address
  function hostText() {
    try {
      const u = gBrowser.currentURI;
      if (u.schemeIs("http") || u.schemeIs("https")) return u.host;
      return "";                      // new tab, about: pages, files: the normal text
    } catch (e) { return ""; }
  }
  function fit() {
    const bar = window.gURLBar, input = bar?.inputField;
    if (!bar || !input || !document.documentElement.hasAttribute("panacea-dock")) return;
    const host = !bar.focused ? hostText() : "";
    // the site's own (coloured) icon before the domain: the same file the island's bar shows
    // (the stored favicon from Places, not the tab's live one, which carries badges like
    // WhatsApp's unread count)
    let img = "";
    if (host) {
      if (icons[host]) img = PathUtils.toFileURI(icons[host]);
      else saveIcon(gBrowser.currentURI.spec).then((f) => { if (f) later(); });
    }
    if (label) {
      if (label.firstChild.getAttribute("src") !== img) label.firstChild.setAttribute("src", img);
      label.firstChild.hidden = !img;
      label.lastChild.textContent = host;
    }
    bar.toggleAttribute("panacea-host", !!host);
    const text = host || input.value || input.placeholder || "";
    const cs = getComputedStyle(input);          // .font can be empty in Firefox: build it
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const hover = bar.matches(":hover");
    // idle: compact, just the domain; hover: a little air around it, like the island's bar
    const chrome = bar.focused ? 96 : (img ? 24 : 0) + (hover ? 72 : 34);
    const max = Math.min(880, window.innerWidth * 0.72);
    const min = bar.focused ? 320 : hover ? 180 : 90;
    const w = Math.round(Math.max(min, Math.min(max, ctx.measureText(text).width + chrome)));
    bar.style.setProperty("--dock-w", w + "px");
  }
  const later = () => requestAnimationFrame(fit);
  function hook() {
    const bar = window.gURLBar;
    if (!bar?.inputField) return;
    label = document.createElementNS("http://www.w3.org/1999/xhtml", "div");
    label.id = "panacea-dock-host";
    const XH = "http://www.w3.org/1999/xhtml";
    label.append(document.createElementNS(XH, "img"), document.createElementNS(XH, "span"));
    label.firstChild.className = "panacea-dock-icon";
    label.firstChild.hidden = true;
    bar.querySelector(".urlbar-input-container")?.appendChild(label);

    // Zen's site-data button stays, invisible, as the anchor for its permission and add-on panels
    const box = bar.querySelector(".urlbar-input-container");
    // a globe at the left while you type (like a normal address bar)
    const globe = document.createElementNS(XH, "div");
    globe.id = "panacea-dock-globe";
    box?.appendChild(globe);
    // Claude mode, while searching (the logo at the right; Ctrl+Shift toggles it, Ctrl+Shift+T
    // opens the search with it on): Enter hands the address or search to the island chat
    // instead of opening it, so Claude opens it and takes your instructions
    const cl = document.createElementNS(XH, "div");
    cl.id = "panacea-dock-claude";
    cl.title = "Send to Claude instead (Ctrl+Shift)";
    cl.setAttribute("role", "button");
    for (const ev of ["mousedown", "mouseup"]) cl.addEventListener(ev, (e) => { e.stopPropagation(); e.preventDefault(); });
    cl.addEventListener("click", (e) => { e.stopPropagation(); e.preventDefault(); setClaude(!bar.hasAttribute("panacea-claude-on")); });
    box?.appendChild(cl);
    function setClaude(on) {
      if (on === bar.hasAttribute("panacea-claude-on")) return;
      bar.toggleAttribute("panacea-claude-on", on);
      if (on) cl.animate([{ rotate: "0deg" }, { rotate: "360deg" }], { duration: 650, easing: "cubic-bezier(0.22, 1, 0.36, 1)" });
    }
    claudeOn = setClaude;
    bar.inputField.addEventListener("blur", () => setTimeout(() => { if (!bar.focused) setClaude(false); }, 0));
    // Enter in Claude mode: the chosen row's address, or what's typed
    bar.inputField.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || !bar.hasAttribute("panacea-claude-on")) return;
      e.preventDefault(); e.stopImmediatePropagation();
      let target = "", search = false;
      try {
        const r = bar.view?.selectedElement?.result;
        if (r?.payload?.url) target = r.payload.url;
        else if (r?.payload?.query) { target = r.payload.query; search = true; }
      } catch (err) {}
      if (!target) { target = bar.value.trim(); search = !!target && !/^[a-z][\w+.-]*:|^[^\s/]+\.[^\s/]{2,}(\/|$)/i.test(target); }
      if (!target) return;
      sendToClaude(target, search);
      bar.view?.close();
      setClaude(false);
      gBrowser.selectedBrowser.focus();
    }, true);
    // Ctrl+Shift on its own (either order), released: toggle (Ctrl+Shift+arrows doesn't)
    let chord = false;
    bar.inputField.addEventListener("keydown", (e) => {
      chord = (e.key === "Shift" && e.ctrlKey) || (e.key === "Control" && e.shiftKey);
    }, true);
    bar.inputField.addEventListener("keyup", (e) => {
      if (chord && (e.key === "Shift" || e.key === "Control")) { chord = false; setClaude(!bar.hasAttribute("panacea-claude-on")); }
    }, true);
    for (const ev of ["input", "focus", "blur"]) bar.inputField.addEventListener(ev, later);
    gBrowser.tabContainer.addEventListener("TabSelect", () => setTimeout(fit, 50));
    // the favicon arrives after the page starts loading
    gBrowser.tabContainer.addEventListener("TabAttrModified", (e) => {
      if (e.target === gBrowser.selectedTab && e.detail?.changed?.includes("image")) later();
    });
    gBrowser.addProgressListener({ onLocationChange: () => setTimeout(fit, 50),
      QueryInterface: ChromeUtils.generateQI(["nsIWebProgressListener", "nsISupportsWeakReference"]) });
    window.addEventListener("resize", later);
    bar.addEventListener("mouseenter", later);
    bar.addEventListener("mouseleave", later);
    setTimeout(fit, 300);

    // the notch's height eases into every change (results open/close, rows come and go):
    // its background starts at the old height and slides to the new one (--dock-grow)
    try { CSS.registerProperty({ name: "--dock-grow", syntax: "<length>", inherits: false, initialValue: "0px" }); } catch (e) {}
    const bg = bar.querySelector(".urlbar-background");
    let lastH = bar.getBoundingClientRect().height;
    new ResizeObserver(() => {
      const h = bar.getBoundingClientRect().height;
      const d = h - lastH;
      lastH = h;
      // small changes (idle <-> hover) are CSS transitions already; this is for the results
      if (!bg || Math.abs(d) < 34 || Math.abs(d) > 1500 || !document.documentElement.hasAttribute("panacea-dock")) return;
      bg.animate([{ "--dock-grow": d + "px" }, { "--dock-grow": "0px" }],
                 { duration: 280, easing: "cubic-bezier(0.22, 1, 0.36, 1)" });
    }).observe(bar);
  }
  // ------------------------------------------------------------ Zen-only mode
  // While Zen is alone on its screen, the Panacea island is the address bar (portal-patch.py
  // in panacea-config). The island writes $XDG_RUNTIME_DIR/panacea-zen-solo ("1 <its pid>");
  // then the dock sinks away ([panacea-solo], panacea-dock.css) and everything that wants
  // the address bar (Ctrl+L, Alt+D, F6, Ctrl+K, Ctrl+T, the new-tab buttons) opens the
  // island instead. The island shows the address from $XDG_RUNTIME_DIR/panacea-zen-tab.json.
  const RUN = Services.env.get("XDG_RUNTIME_DIR") || "/tmp";
  const SOLO = PathUtils.join(RUN, "panacea-zen-solo");
  const TABF = PathUtils.join(RUN, "panacea-zen-tab.json");
  const QS_DIR = PathUtils.join(Services.dirsvc.get("Home", Ci.nsIFile).path, ".config", "panacea");
  let solo = false, soloPid = "", soloMtime = 0, soloTick = 0, Subprocess = null;
  const isSolo = () => solo && document.documentElement.hasAttribute("panacea-dock");

  // the island chat, with the page filled in (you add what to do, then send)
  let claudeOn = () => {};
  function sendToClaude(target, search) {
    const draft = `${search ? "Search in Zen" : "Open in Zen"}: ${target}\n`;
    island("askAbout", JSON.stringify({ draft, send: false }));
  }
  function island(fn, ...args) {
    try {
      Subprocess ??= ChromeUtils.importESModule("resource://gre/modules/Subprocess.sys.mjs").Subprocess;
      Subprocess.call({ command: "/usr/bin/qs", arguments: ["-p", QS_DIR, "ipc", "call", "pill", fn, ...args] })
        .then((p) => p.wait()).catch(() => {});
    } catch (e) {}
  }
  async function alive(pid) {   // the island that wrote the file is still running
    // (/proc files report size 0, so IOUtils can't read them: just check the process is there)
    try { return /^\d+$/.test(pid) && await IOUtils.exists(`/proc/${pid}/status`); }
    catch (e) { return false; }
  }
  async function readSolo() {
    let on = solo;
    try {
      const st = await IOUtils.stat(SOLO);
      if (st.lastModified !== soloMtime || ++soloTick % 8 === 0) {   // re-check the pid every 2 s
        soloMtime = st.lastModified;
        const [flag, pid] = (await IOUtils.readUTF8(SOLO)).trim().split(/\s+/);
        soloPid = pid || "";
        // island mode: the dock stays hidden whenever the island is running, whatever the flag
        on = (flag === "1" || urlbarMode() === "island") && !!soloPid && await alive(soloPid);
      }
    } catch (e) { on = false; }
    if (on === solo) return;
    solo = on;
    document.documentElement.toggleAttribute("panacea-solo", on);
    if (on && window.gURLBar?.focused) { gURLBar.view?.close(); gBrowser.selectedBrowser.focus(); }
  }
  setInterval(readSolo, 250);
  readSolo();

  // the address-bar mode, for the island too ($XDG_RUNTIME_DIR/panacea-zen-mode)
  const MODE_PREF = "panacea.zen.urlbar";
  const MODE_FILE = PathUtils.join(RUN, "panacea-zen-mode");
  function urlbarMode() {
    return Services.prefs.getStringPref(MODE_PREF, "dock") === "island" ? "island" : "dock";
  }
  if (!Services.prefs.prefHasUserValue(MODE_PREF)) Services.prefs.setStringPref(MODE_PREF, "dock");
  function writeMode() {
    IOUtils.writeUTF8(MODE_FILE, urlbarMode() + "\n").catch(() => {});   // in place: the island watches it
    soloMtime = 0;                                                       // re-read the island's flag now
    readSolo();
  }
  const modeObserver = { observe: writeMode };
  Services.prefs.addObserver(MODE_PREF, modeObserver);
  window.addEventListener("unload", () => Services.prefs.removeObserver(MODE_PREF, modeObserver), { once: true });
  writeMode();

  // Ctrl+Shift+T: the search with Claude mode on (Ctrl+T stays a normal new tab). This takes
  // the key from "reopen closed tab" (still in the History menu and the island's Zen tab).
  const CLAUDE_FLAG = PathUtils.join(RUN, "panacea-zen-claude");
  let claudeKeyAt = 0;
  window.addEventListener("keydown", (e) => {
    if (e.code !== "KeyT" || !e.ctrlKey || !e.shiftKey || e.altKey || e.metaKey) return;
    if (!document.documentElement.hasAttribute("panacea-dock")) return;
    e.preventDefault(); e.stopImmediatePropagation();
    claudeKeyAt = Date.now();
    if (isSolo()) {
      IOUtils.writeUTF8(CLAUDE_FLAG, String(Date.now()) + "\n").then(() => island("zenBarNew")).catch(() => island("zenBarNew"));
      return;
    }
    gURLBar.value = "";
    gURLBar.focus();
    claudeOn(true);
  }, true);
  window.addEventListener("command", (e) => {   // in case the keyset still fires it
    const t = e.target, id = t?.id || "", cmd = t?.getAttribute?.("command") || "";
    if (Date.now() - claudeKeyAt < 400 && (id === "History:UndoCloseTab" || cmd === "History:UndoCloseTab")) {
      e.stopPropagation(); e.preventDefault();
    }
  }, true);

  // the keys: Browser:OpenLocation (Ctrl+L, Alt+D, F6), Tools:Search (Ctrl+K, Ctrl+E)
  window.addEventListener("command", (e) => {
    if (!isSolo()) return;
    const t = e.target, id = t?.id || "", cmd = t?.getAttribute?.("command") || "";
    if (/^(Browser:OpenLocation|Tools:Search)$/.test(id) || /^(Browser:OpenLocation|Tools:Search)$/.test(cmd)) {
      e.stopPropagation(); e.preventDefault();
      island("zenBar");
    }
  }, true);

  // site icons, for the island: $XDG_RUNTIME_DIR/panacea-zen-icons/<host>.<ext>, listed in
  // index.json ({host: file}). Open tabs, the active one, and your most visited sites.
  const ICONS = PathUtils.join(RUN, "panacea-zen-icons");
  const INDEX = PathUtils.join(ICONS, "index.json");
  const icons = {}, asked = new Set();
  const ICON_V = ".i2";                     // bumped when the saved icons change (i2: dark ones lightened)
  let indexTimer = null;
  const hostOf = (spec) => { try { return Services.io.newURI(spec).host; } catch (e) { return ""; } };
  async function saveIcon(spec) {
    const host = hostOf(spec);
    if (!host || !/^https?:/.test(spec)) return "";
    if (icons[host]) return icons[host];
    if (asked.has(spec)) return "";
    asked.add(spec);
    try {
      const fav = await PlacesUtils.favicons.getFaviconForPage(Services.io.newURI(spec));
      if (!fav || !fav.rawData || !fav.rawData.length) return "";
      const mt = fav.mimeType || "";
      const ext = /svg/.test(mt) ? "svg" : /png/.test(mt) ? "png" : /jpe?g/.test(mt) ? "jpg"
                : /webp/.test(mt) ? "webp" : /gif/.test(mt) ? "gif" : "ico";
      const base = PathUtils.join(ICONS, host.replace(/[^a-z0-9.-]/gi, "_") + ICON_V);
      await IOUtils.makeDirectory(ICONS, { ignoreExisting: true, permissions: 0o700 });
      // a dark one-colour icon on a transparent background (GitHub's, X's...) would vanish on
      // the black island and dock: it's saved with its colours inverted, as a PNG
      const light = await lightened(fav.rawData, mt || "image/" + ext);
      const file = light ? base + ".png" : base + "." + ext;
      await IOUtils.write(file, light || new Uint8Array(fav.rawData));
      icons[host] = file;
      clearTimeout(indexTimer);
      indexTimer = setTimeout(() => IOUtils.writeUTF8(INDEX, JSON.stringify(icons) + "\n").catch(() => {}), 300);
      return file;
    } catch (e) { return ""; }
  }
  // dark, nearly colourless, with real transparency around it -> inverted PNG bytes; else null
  async function lightened(raw, mime) {
    let url = "";
    try {
      url = URL.createObjectURL(new Blob([new Uint8Array(raw)], { type: mime }));
      const img = new Image();
      img.src = url;
      await img.decode();
      const N = 64;
      const c = document.createElementNS("http://www.w3.org/1999/xhtml", "canvas");
      c.width = c.height = N;
      const g = c.getContext("2d", { willReadFrequently: true });
      g.drawImage(img, 0, 0, N, N);
      const px = g.getImageData(0, 0, N, N), d = px.data;
      let solid = 0, clear = 0, luma = 0, sat = 0;
      for (let i = 0; i < d.length; i += 4) {
        if (d[i + 3] < 40) { clear++; continue; }
        if (d[i + 3] < 128) continue;
        const r = d[i], gr = d[i + 1], b = d[i + 2], mx = Math.max(r, gr, b), mn = Math.min(r, gr, b);
        solid++;
        luma += (0.2126 * r + 0.7152 * gr + 0.0722 * b) / 255;
        sat += mx ? (mx - mn) / mx : 0;
      }
      if (!solid || clear / (N * N) < 0.12) return null;          // a filled tile carries its own background
      if (luma / solid > 0.3 || sat / solid > 0.3) return null;   // light enough, or coloured
      for (let i = 0; i < d.length; i += 4) { d[i] = 255 - d[i]; d[i + 1] = 255 - d[i + 1]; d[i + 2] = 255 - d[i + 2]; }
      g.putImageData(px, 0, 0);
      const blob = await new Promise((res) => c.toBlob(res, "image/png"));
      return blob ? new Uint8Array(await blob.arrayBuffer()) : null;
    } catch (e) { return null; }
    finally { if (url) URL.revokeObjectURL(url); }
  }
  async function seedIcons() {
    // only files saved by this version (older ones were never checked for dark icons)
    try { const old = JSON.parse(await IOUtils.readUTF8(INDEX)); for (const h in old) if (old[h].includes(ICON_V + ".") && await IOUtils.exists(old[h])) icons[h] = old[h]; } catch (e) {}
    for (const t of gBrowser.tabs) { const s = t.linkedBrowser?.currentURI?.spec; if (s) await saveIcon(s); }
    try {
      const db = await PlacesUtils.promiseDBConnection();
      const rows = await db.execute(
        "SELECT url FROM moz_places WHERE frecency > 0 AND url LIKE 'http%' ORDER BY frecency DESC LIMIT 600");
      const seen = new Set();
      for (const r of rows) {
        const u = r.getResultByName("url"), h = hostOf(u);
        if (!h || seen.has(h)) continue;
        seen.add(h);
        await saveIcon(u);
        if (seen.size >= 250) break;
      }
    } catch (e) {}
  }

  // the active tab, for the island
  let lastTab = "", tabTimer = null;
  async function writeTab() {
    if (Services.wm.getMostRecentWindow("navigator:browser") !== window) return;
    try {
      const u = gBrowser.currentURI;
      let host = "";
      try { host = u.host; } catch (e) {}
      const icon = await saveIcon(u.spec);
      const data = JSON.stringify({ url: u.displaySpec, title: gBrowser.selectedTab?.label || "", host, icon });
      if (data === lastTab) return;
      lastTab = data;
      IOUtils.writeUTF8(TABF, data + "\n").catch(() => {});   // in place: the island watches the file
    } catch (e) {}
  }
  const tabLater = () => { clearTimeout(tabTimer); tabTimer = setTimeout(writeTab, 60); };

  // pinned and recent tabs, for the island's Zen tab ($XDG_RUNTIME_DIR/panacea-zen-tabs.json)
  const TABS = PathUtils.join(RUN, "panacea-zen-tabs.json");
  let lastTabs = "", tabsTimer = null;
  const mainWindow = () => Services.wm.getMostRecentWindow("navigator:browser") === window;
  async function tabInfo(t) {
    const spec = t.linkedBrowser?.currentURI?.spec || "";
    const host = hostOf(spec);
    return { key: t.linkedPanel || "", title: t.label || spec, url: spec, host,
             icon: icons[host] || (await saveIcon(spec)) || "",
             essential: t.hasAttribute("zen-essential"), selected: t === gBrowser.selectedTab };
  }
  async function writeTabs() {
    if (!mainWindow()) return;
    try {
      const all = [...gBrowser.tabs].filter((t) => !t.closing && !t.hasAttribute("zen-empty-tab") && !t.hasAttribute("zen-glance-tab"));
      const pinned = all.filter((t) => t.pinned).slice(0, 24);
      const recent = all.filter((t) => !t.pinned)
        .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0)).slice(0, 8);
      let closed = 0;
      try { closed = SessionStore.getClosedTabCountForWindow(window); } catch (e) {}
      const data = JSON.stringify({ pinned: await Promise.all(pinned.map(tabInfo)),
                                    recent: await Promise.all(recent.map(tabInfo)), closed });
      if (data === lastTabs) return;
      lastTabs = data;
      IOUtils.writeUTF8(TABS, data + "\n").catch(() => {});
    } catch (e) {}
  }
  const tabsLater = () => { clearTimeout(tabsTimer); tabsTimer = setTimeout(writeTabs, 250); };

  // the island's commands ($XDG_RUNTIME_DIR/panacea-zen-cmd: "select <key>", "close <key>", "undoClose")
  const CMD = PathUtils.join(RUN, "panacea-zen-cmd");
  let cmdMtime = null;
  async function readCmd() {
    if (!mainWindow()) return;
    let st;
    try { st = await IOUtils.stat(CMD); } catch (e) { cmdMtime = 0; return; }
    if (cmdMtime === null) { cmdMtime = st.lastModified; return; }   // an old command from before
    if (st.lastModified === cmdMtime) return;
    cmdMtime = st.lastModified;
    let line = "";
    try { line = (await IOUtils.readUTF8(CMD)).trim(); } catch (e) { return; }
    const i = line.indexOf(" "), cmd = i < 0 ? line : line.slice(0, i), arg = i < 0 ? "" : line.slice(i + 1);
    const tab = arg ? [...gBrowser.tabs].find((t) => t.linkedPanel === arg) : null;
    try {
      if (cmd === "select" && tab) {
        if (window.gZenWorkspaces?.switchTabIfNeeded) await gZenWorkspaces.switchTabIfNeeded(tab);
        else gBrowser.selectedTab = tab;
      } else if (cmd === "close" && tab) gBrowser.removeTab(tab, { animate: true });
      else if (cmd === "undoClose") window.undoCloseTab?.();
    } catch (e) {}
  }
  setInterval(readCmd, 200);

  function hookSolo() {
    // new tabs (Ctrl+T, the sidebar's + and the rest) all ask Zen's handleNewTab first
    const ui = window.gZenUIManager;
    if (ui?.handleNewTab && !ui.__panaceaSolo) {
      const orig = ui.handleNewTab;
      ui.handleNewTab = function (passedURL, ...rest) {
        if (!passedURL && isSolo()) { island("zenBarNew"); return true; }
        return orig.call(this, passedURL, ...rest);
      };
      ui.__panaceaSolo = true;
    }
    // anything else that focuses the hidden bar gets the island instead
    window.gURLBar?.inputField?.addEventListener("focus", () => {
      if (!isSolo()) return;
      setTimeout(() => { gURLBar.view?.close(); gBrowser.selectedBrowser.focus(); island("zenBar"); }, 0);
    });
    gBrowser.tabContainer.addEventListener("TabSelect", tabLater);
    gBrowser.tabContainer.addEventListener("TabAttrModified", (e) => {
      if (e.detail?.changed?.includes("image")) { const s = e.target.linkedBrowser?.currentURI?.spec; if (s) { asked.delete(s); saveIcon(s); } }
      if (e.target === gBrowser.selectedTab) tabLater();
    });
    gBrowser.addProgressListener({ onLocationChange: tabLater,
      QueryInterface: ChromeUtils.generateQI(["nsIWebProgressListener", "nsISupportsWeakReference"]) });
    window.addEventListener("activate", tabLater);
    for (const ev of ["TabOpen", "TabClose", "TabSelect", "TabPinned", "TabUnpinned", "TabMove"])
      gBrowser.tabContainer.addEventListener(ev, tabsLater);
    gBrowser.tabContainer.addEventListener("TabAttrModified", tabsLater);
    window.addEventListener("activate", tabsLater);
    tabLater();
    tabsLater();
    if (Services.wm.getMostRecentWindow("navigator:browser") === window) setTimeout(seedIcons, 4000);
  }

  if (document.readyState === "complete") { hook(); hookSolo(); }
  else window.addEventListener("load", () => { hook(); hookSolo(); }, { once: true });
})();
