// ==UserScript==
// @name        Panacea home
// @description Zen's start and new-tab page: chrome/home/index.html, served from inside Zen
//              at resource://panacea-home/ (no server, no extension).
// ==/UserScript==
// Part of panacea-config (zen/home). Off: about:config, panacea.zen.home = false (and restart).
(function () {
  const PREF = "panacea.zen.home";
  if (!Services.prefs.prefHasUserValue(PREF)) Services.prefs.setBoolPref(PREF, true);
  if (!Services.prefs.getBoolPref(PREF, true)) return;

  const HOME = "resource://panacea-home/index.html";
  const dir = PathUtils.join(PathUtils.profileDir, "chrome", "home");

  // resource://panacea-home/ -> <profile>/chrome/home/ (once per session; harmless again)
  try {
    const res = Services.io.getProtocolHandler("resource").QueryInterface(Ci.nsIResProtocolHandler);
    if (!res.hasSubstitution("panacea-home")) {
      const f = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);
      f.initWithPath(dir);
      res.setSubstitution("panacea-home", Services.io.newFileURI(f));
    }
  } catch (e) { console.error("panacea-home: substitution", e); return; }

  // new tabs and the start page. Zen's "empty tab" (the grey page with the floating
  // url bar) is replaced by real new tabs, which now open this page.
  try {
    const { AboutNewTab } = ChromeUtils.importESModule("resource:///modules/AboutNewTab.sys.mjs");
    AboutNewTab.newTabURL = HOME;
  } catch (e) { console.error("panacea-home: newtab", e); }
  const setDefault = (name, value) => {
    if (Services.prefs.getStringPref(name, "") !== value) Services.prefs.setStringPref(name, value);
  };
  setDefault("browser.startup.homepage", HOME);
  if (Services.prefs.getBoolPref("zen.urlbar.replace-newtab", true)) Services.prefs.setBoolPref("zen.urlbar.replace-newtab", false);

  // the address bar stays empty on it (like on about:newtab)
  try { if (window.gInitialPages && !window.gInitialPages.includes(HOME)) window.gInitialPages.push(HOME); } catch (e) {}
})();
