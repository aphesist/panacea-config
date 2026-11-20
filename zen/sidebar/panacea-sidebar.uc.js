// ==UserScript==
// @name        Panacea sidebar
// @description The sidebar's bottom row: extensions and Zen settings in place of the "+"
//              (Zen's create-new button, hidden in panacea-dark.css).
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

  function start() {
    let tries = 0;
    const t = setInterval(() => { const a = add(), b = addLogo(); if ((a && b) || ++tries > 40) clearInterval(t); }, 250);
  }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start, { once: true });
})();
