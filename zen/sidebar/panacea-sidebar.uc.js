// ==UserScript==
// @name        Panacea sidebar
// @description The sidebar's bottom row: extensions and Zen settings in place of the "+"
//              (Zen's create-new button, hidden in panacea-dark.css); Zen's logo; in compact
//              mode the pill's height follows the tabs; the selected tab's colour for its nub.
// ==/UserScript==
// Part of panacea-config (zen/sidebar).
(function () {
  const XUL = (tag) => document.createXULElement(tag);

  function button(id, label, icon, onCommand) {
    const b = XUL("toolbarbutton");
    b.id = id;
    b.className = "toolbarbutton-1 chromeclass-toolbar-additional panacea-foot-btn";
    b.setAttribute("label", label);
    b.setAttribute("tooltiptext", label);
    b.setAttribute("removable", "false");
    b.style.listStyleImage = `url("${icon}")`;
    b.addEventListener("command", onCommand);
    return b;
  }

  // Zen's openPreferences() switches to an open settings tab wherever it is, Space and all
  // (so it could jump to the Claude Space): only reuse one in the current Space
  function openSettingsHere() {
    const ws = window.gZenWorkspaces?.activeWorkspace || "";
    const here = [...gBrowser.tabs].find((t) =>
      /^about:(preferences|settings)/.test(t.linkedBrowser?.currentURI?.spec || "") &&
      (!ws || t.getAttribute("zen-workspace-id") === ws));
    if (here) { gBrowser.selectedTab = here; return; }
    gBrowser.selectedTab = gBrowser.addTrustedTab("about:preferences");
  }

  function add() {
    const foot = document.getElementById("zen-sidebar-foot-buttons");
    if (!foot) return false;
    if (document.getElementById("panacea-foot-extensions")) return true;
    // extensions: Zen's own panel, anchored here (Zen opens it upward from the footer)
    const ext = button("panacea-foot-extensions", "Extensions",
      "chrome://mozapps/skin/extensions/extension.svg",
      (e) => { try { gUnifiedExtensions.togglePanel(e, null, undefined, undefined, ext); }
               catch (err) { BrowserAddonUI.openAddonsMgr("addons://list/extension"); } });
    const prefs = button("panacea-foot-settings", "Settings",
      "chrome://global/skin/icons/settings.svg",
      () => openSettingsHere());
    foot.append(ext, prefs);
    return true;
  }

  // Zen's logo at the top of the sidebar, right above the pinned tiles (styled in
  // panacea-dark.css). Not in #zen-sidebar-top-buttons: Zen's single-toolbar layout moves that
  // into the top bar, which the dock layout folds away.
  function addLogo() {
    const ess = document.getElementById("zen-essentials");
    if (!ess) return false;
    let logo = document.getElementById("panacea-zen-logo");
    if (!logo) {
      logo = document.createElementNS("http://www.w3.org/1999/xhtml", "div");
      logo.id = "panacea-zen-logo";
    }
    if (logo.nextElementSibling !== ess) ess.before(logo);
    // where it ended up, for checking ($XDG_RUNTIME_DIR/panacea-zen-logo.json)
    setTimeout(() => {
      try {
        const r = logo.getBoundingClientRect(), cs = getComputedStyle(logo);
        const run = Services.env.get("XDG_RUNTIME_DIR") || "/tmp";
        IOUtils.writeUTF8(PathUtils.join(run, "panacea-zen-logo.json"), JSON.stringify({
          parent: logo.parentNode?.id || logo.parentNode?.localName, rect: [r.x, r.y, r.width, r.height],
          display: cs.display, bg: cs.backgroundImage.slice(0, 40) }) + "\n").catch(() => {});
      } catch (e) {}
    }, 3000);
    return true;
  }

  // ---------------------------------------------------------------- compact mode: the pill's height
  // follows the tabs (panacea-dock.css: --panacea-sidebar-h), up to 90% of the window; past that
  // the tabs scroll. Height = the pill's fixed parts (logo, Essentials, buttons) + the tab list's
  // full content height. The tab list is an arrowscrollbox whose inner scrollbox knows the latter.
  let sizeFrame = 0;
  function fitPill() {
    sizeFrame = 0;
    const root = document.documentElement;
    if (root.getAttribute("zen-compact-mode") !== "true") { root.style.removeProperty("--panacea-sidebar-h"); return; }
    const bar = document.getElementById("titlebar");
    const ws = window.gZenWorkspaces?.activeWorkspaceElement;
    const list = ws?.scrollbox, inner = list?.scrollbox;
    if (!bar || !list || !inner) return;
    markIndicators();
    const empty = ws.querySelector(".zen-workspace-empty-space");
    const fixed = bar.getBoundingClientRect().height - list.getBoundingClientRect().height
                  - (empty ? empty.getBoundingClientRect().height : 0);
    const want = Math.round(fixed + inner.scrollHeight);
    const cap = Math.round(window.innerHeight * 0.9);
    const h = Math.max(160, Math.min(want, cap));
    if (root.style.getPropertyValue("--panacea-sidebar-h") !== h + "px") root.style.setProperty("--panacea-sidebar-h", h + "px");
    dumpLater({ fixed, content: inner.scrollHeight, want, cap, h });
  }

  // ---------------------------------------------------------------- layout dump, for tuning the CSS
  // from outside: $XDG_RUNTIME_DIR/panacea-zen-sidebar.json (boxes and a few computed styles of the
  // sidebar's parts). $XDG_RUNTIME_DIR/panacea-zen-sidebar-cmd: "dump", "show" (hold the sidebar
  // open, as Zen's own toggle does) or "hide". Read-only otherwise.
  const RUN = Services.env.get("XDG_RUNTIME_DIR") || "/tmp";
  let dumpTimer = 0, lastFit = null;
  function dumpLater(fit) { if (fit) lastFit = fit; clearTimeout(dumpTimer); dumpTimer = setTimeout(dump, 700); }
  function dump() {
    try {
      const ws = window.gZenWorkspaces?.activeWorkspaceElement;
      const parts = {
        toolbox: document.getElementById("navigator-toolbox"), titlebar: document.getElementById("titlebar"),
        background: document.getElementById("zen-toolbar-background"), top: document.getElementById("zen-sidebar-top-buttons"),
        logo: document.getElementById("panacea-zen-logo"), TabsToolbar: document.getElementById("TabsToolbar"),
        items: document.querySelector("#TabsToolbar > .toolbar-items"), target: document.getElementById("TabsToolbar-customization-target"),
        tabs: document.getElementById("tabbrowser-tabs"), essentials: document.getElementById("zen-essentials"),
        wrapper: document.getElementById("zen-tabs-wrapper"), workspace: ws, list: ws?.scrollbox,
        empty: ws?.querySelector(".zen-workspace-empty-space"), foot: document.getElementById("zen-sidebar-foot-buttons"),
        selected: gBrowser.selectedTab,
      };
      const out = { fit: lastFit, window: [window.innerWidth, window.innerHeight],
                    attrs: Object.fromEntries([...parts.toolbox.attributes].map((a) => [a.name, a.value])) };
      for (const [k, el] of Object.entries(parts)) {
        if (!el) { out[k] = null; continue; }
        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        out[k] = { rect: [r.x, r.y, r.width, r.height].map(Math.round), display: cs.display, position: cs.position,
                   height: cs.height, minH: cs.minHeight, flex: cs.flex, overflow: cs.overflow, padding: cs.padding,
                   margin: cs.margin, clip: cs.clipPath.slice(0, 60), parent: el.parentNode?.id || el.parentNode?.localName };
      }
      if (ws?.scrollbox?.scrollbox) out.listInner = { scrollH: ws.scrollbox.scrollbox.scrollHeight, clientH: ws.scrollbox.scrollbox.clientHeight };
      IOUtils.writeUTF8(PathUtils.join(RUN, "panacea-zen-sidebar.json"), JSON.stringify(out, null, 1) + "\n").catch(() => {});
    } catch (e) {
      IOUtils.writeUTF8(PathUtils.join(RUN, "panacea-zen-sidebar.json"), JSON.stringify({ error: String(e) }) + "\n").catch(() => {});
    }
  }
  const CMD = PathUtils.join(RUN, "panacea-zen-sidebar-cmd");
  let cmdMtime = null;
  async function readCmd() {
    if (window !== Services.wm.getMostRecentWindow("navigator:browser")) return;
    let st;
    try { st = await IOUtils.stat(CMD); } catch (e) { cmdMtime = 0; return; }
    if (cmdMtime === null) { cmdMtime = st.lastModified; return; }
    if (st.lastModified === cmdMtime) return;
    cmdMtime = st.lastModified;
    const cmd = (await IOUtils.readUTF8(CMD).catch(() => "")).trim();
    const tb = document.getElementById("navigator-toolbox");
    if (cmd === "show") tb?.setAttribute("zen-user-show", "true");
    else if (cmd === "hide") tb?.removeAttribute("zen-user-show");
    if (cmd === "show") { fitPill(); setTimeout(dump, 900); } else dump();
  }
  setInterval(readCmd, 400);
  // a Space whose indicator row carries a picture (claude-space.css draws the pixel Claude there)
  // keeps that row; the others' rows are hidden (panacea-dock.css)
  function markIndicators() {
    for (const w of document.querySelectorAll("zen-workspace")) {
      const ind = w.querySelector(".zen-current-workspace-indicator");
      let pic = false;
      try { pic = !!ind && getComputedStyle(ind, "::after").backgroundImage.startsWith("url("); } catch (e) {}
      w.toggleAttribute("panacea-keep-indicator", pic);
    }
  }
  const fitLater = () => { if (!sizeFrame) sizeFrame = requestAnimationFrame(() => requestAnimationFrame(fitPill)); };

  // ---------------------------------------------------------------- the selected tab's colour
  // (the nub beside it, panacea-dock.css): the most common vivid colour of its icon; a grey or
  // black-and-white icon gets the text colour.
  const colorCache = new Map();
  function iconColor(img) {
    const src = img?.currentSrc || img?.src || "";
    if (!src || !img.complete || !img.naturalWidth) return null;
    if (colorCache.has(src)) return colorCache.get(src);
    let out = "";
    try {
      const c = document.createElementNS("http://www.w3.org/1999/xhtml", "canvas");
      c.width = c.height = 24;
      const g = c.getContext("2d", { willReadFrequently: true });
      g.drawImage(img, 0, 0, 24, 24);
      const d = g.getImageData(0, 0, 24, 24).data;
      const bins = new Map();
      for (let i = 0; i < d.length; i += 4) {
        const r = d[i], gg = d[i + 1], b = d[i + 2], a = d[i + 3];
        if (a < 160) continue;
        const max = Math.max(r, gg, b), min = Math.min(r, gg, b), l = (max + min) / 2;
        const sat = max === min ? 0 : (max - min) / (255 - Math.abs(max + min - 255));
        if (sat < 0.35 || l < 40 || l > 235) continue;
        let h = 0;
        if (max === r) h = ((gg - b) / (max - min)) % 6; else if (max === gg) h = (b - r) / (max - min) + 2; else h = (r - gg) / (max - min) + 4;
        const key = Math.round(((h * 60 + 360) % 360) / 20);
        const e = bins.get(key) || { n: 0, r: 0, g: 0, b: 0 };
        const w = sat;                                      // vivid pixels count more
        e.n += w; e.r += r * w; e.g += gg * w; e.b += b * w;
        bins.set(key, e);
      }
      let best = null;
      for (const e of bins.values()) if (!best || e.n > best.n) best = e;
      if (best && best.n > 6) out = `rgb(${Math.round(best.r / best.n)}, ${Math.round(best.g / best.n)}, ${Math.round(best.b / best.n)})`;
    } catch (e) { return null; }
    colorCache.set(src, out);
    return out;
  }
  function paintTab(tab) {
    if (!tab) return;
    const img = tab.querySelector(".tab-icon-image");
    const col = iconColor(img);
    if (col === null) { if (img && !img.complete) img.addEventListener("load", () => paintTab(tab), { once: true }); return; }
    if (col) tab.style.setProperty("--panacea-tab-color", col); else tab.style.removeProperty("--panacea-tab-color");
  }

  function watch() {
    const tc = gBrowser.tabContainer;
    for (const ev of ["TabOpen", "TabClose", "TabPinned", "TabUnpinned", "TabMove", "TabShow", "TabHide",
                      "TabGroupCreate", "TabGroupRemoved", "TabGroupCollapse", "TabGroupExpand"])
      tc.addEventListener(ev, fitLater);
    tc.addEventListener("TabSelect", (e) => paintTab(e.target));
    tc.addEventListener("TabAttrModified", (e) => {
      if (e.target.selected && e.detail?.changed?.includes("image")) paintTab(e.target);
    });
    window.addEventListener("ZenWorkspacesUIUpdate", fitLater);
    window.addEventListener("resize", fitLater);
    // the moment it opens (and while open: a Space switch, a tab loading its title...), measure again
    const tb = document.getElementById("navigator-toolbox");
    const shownAttrs = ["zen-has-hover", "zen-user-show", "zen-has-empty-tab", "flash-popup", "has-popup-menu", "movingtab", "zen-compact-mode-active"];
    new MutationObserver(fitLater).observe(tb, { attributes: true, attributeFilter: shownAttrs });
    setInterval(() => { if (shownAttrs.some((a) => tb.hasAttribute(a))) fitPill(); }, 700);
    gBrowser.tabContainer.addEventListener("TabSelect", fitLater);
    new MutationObserver(fitLater).observe(document.documentElement,
      { attributes: true, attributeFilter: ["zen-compact-mode", "zen-sidebar-expanded", "zen-workspace-id"] });
    // tabs folding/unfolding, a long title wrapping...: any size change of the lists
    const ro = new ResizeObserver(fitLater);
    const seen = new WeakSet();
    const observeLists = () => {
      for (const el of document.querySelectorAll("zen-workspace .zen-workspace-tabs-section, #zen-essentials"))
        if (!seen.has(el)) { seen.add(el); ro.observe(el); }
    };
    observeLists();
    window.addEventListener("ZenWorkspacesUIUpdate", observeLists);
    paintTab(gBrowser.selectedTab);
    fitLater();
  }

  function start() {
    let tries = 0;
    const t = setInterval(() => { const a = add(), b = addLogo(); if ((a && b) || ++tries > 40) clearInterval(t); }, 250);
    let wtries = 0;
    const w = setInterval(() => {
      if (window.gBrowser?.tabContainer && window.gZenWorkspaces?.activeWorkspaceElement) { clearInterval(w); watch(); }
      else if (++wtries > 80) clearInterval(w);
    }, 250);
  }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start, { once: true });
})();
