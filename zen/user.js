// Load chrome/userChrome.css (Zen ships with it off)
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("widget.use-xdg-desktop-portal.file-picker", 1);  // Panacea island file picker
user_pref("media.webrtc.capture.allow-pipewire", true);  // screen sharing through PipeWire + Hyprland's picker (X11 capture is black on Wayland)
