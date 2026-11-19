// Load chrome/userChrome.css (Zen ships with it off)
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("widget.use-xdg-desktop-portal.file-picker", 1);  // Panacea island file picker
user_pref("media.webrtc.capture.allow-pipewire", true);  // screen sharing through PipeWire + Hyprland's picker (X11 capture is black on Wayland)
user_pref("browser.display.background_color.dark", "#0e0e0e");  // blank pages: Panacea near-black, not grey
user_pref("zen.urlbar.behavior", "default");  // url bar stays in place when focused; results drop down under it (no floating/cut-off bar)
user_pref("layout.css.field-sizing.enabled", true);  // Panacea dock: the url pill sizes to its text
user_pref("privacy.query_stripping.enabled", true);  // strip tracking parameters from links
user_pref("privacy.query_stripping.enabled.pbmode", true);
user_pref("privacy.query_stripping.strip_on_share.enabled", true);  // "Copy clean link"
