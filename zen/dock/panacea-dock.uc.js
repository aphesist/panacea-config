// ==UserScript==
// @name        Panacea dock
// @description Loads chrome/panacea-dock.css (the bottom url-bar dock layout) while the
//              pref panacea.zen.dock is true, and reloads it live when the file changes.
// ==/UserScript==
// Part of panacea-config (zen/dock). Turn the layout off: about:config, panacea.zen.dock = false.
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
    if (label) label.textContent = host;
    bar.toggleAttribute("panacea-host", !!host);
    const text = host || input.value || input.placeholder || "";
    const cs = getComputedStyle(input);          // .font can be empty in Firefox: build it
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const hover = bar.matches(":hover");
    // idle: compact, just the domain; hover: room for the two edge buttons
    const chrome = bar.focused || hover ? 96 : 34;
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
    bar.querySelector(".urlbar-input-container")?.appendChild(label);

    // our own two buttons (Zen's are hidden; its site-data button stays as the panel anchor)
    const box = bar.querySelector(".urlbar-input-container");
    const mk = (id, title) => {
      const b = document.createElementNS("http://www.w3.org/1999/xhtml", "div");
      b.id = id; b.className = "panacea-dock-btn"; b.title = title;
      b.setAttribute("role", "button");
      for (const ev of ["mousedown", "mouseup"]) b.addEventListener(ev, (e) => e.stopPropagation());
      box?.appendChild(b);
      return b;
    };
    const copy = mk("panacea-dock-copy", "Copy link");
    copy.addEventListener("click", (e) => {
      e.stopPropagation(); e.preventDefault();
      try {
        Cc["@mozilla.org/widget/clipboardhelper;1"].getService(Ci.nsIClipboardHelper)
          .copyString(gBrowser.currentURI.displaySpec);
        copy.setAttribute("done", "true");
        setTimeout(() => copy.removeAttribute("done"), 1400);
      } catch (err) {}
    });
    const site = mk("panacea-dock-site", "Site settings and extensions");
    site.addEventListener("click", (e) => {
      e.stopPropagation(); e.preventDefault();
      // Zen's own handler, anchored to our button (its button is hidden, so it won't open)
      const p = window.gZenSiteDataPanel;
      if (p) window.gUnifiedExtensions.togglePanel(e, null, p.unifiedPanel, p.unifiedPanelView, site);
    });
    for (const ev of ["input", "focus", "blur"]) bar.inputField.addEventListener(ev, later);
    gBrowser.tabContainer.addEventListener("TabSelect", () => setTimeout(fit, 50));
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
  if (document.readyState === "complete") hook();
  else window.addEventListener("load", hook, { once: true });
})();
