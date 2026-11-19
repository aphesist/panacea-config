<div align="center">

# panacea-config

**My layer on top of [Panacea Shell](https://github.com/EnsixD/Panacea)**

![Panacea](https://img.shields.io/badge/Panacea-1.0.24-18181b)
![Hyprland](https://img.shields.io/badge/Hyprland-0.57_Lua-ffffff)
![Update-safe](https://img.shields.io/badge/survives-Panacea_updates-888888)
![License](https://img.shields.io/badge/license-MIT-d71920)

[Screenshots](#screenshots) · [What changes](#what-changes) · [Fresh install](#from-a-fresh-arch-install) · [How patches survive updates](#how-patches-survive-updates)

</div>

<div align="center">

<img src="docs/img/desktop.jpg" width="860" alt="The desktop: Panacea's island at the top edge over a dark teal wallpaper">

</div>

Panacea keeps a handful of folders untouched across updates:
`hypr/custom/`, `fish/custom/`, `foot/custom.ini` and `panacea/scripts/custom/`.
Everything here lives in those folders. A few Panacea files are patched in place:
the lock screen, the vault script and the file manager (for the island file picker). Their patchers are idempotent,
all-or-nothing, and re-run themselves whenever an update replaces the file.

## Screenshots

### Lock screen

A bare fingerprint glyph at the bottom: just touch the sensor at any time. After a restart it asks for your password once, which also unlocks the keyring, then it's fingerprint only. It pulses when ready, shakes on a miss, and the unlock fades into the desktop.

<img src="docs/img/lock.jpg" width="860" alt="Panacea lock screen with clock and a fingerprint indicator reading 'Touch the sensor to unlock'">

### Claude in the island

`Super+C` opens a single Claude tab, cursor in the message box: the Claude
logo, model pills, a little orange pixel Claude on the empty chat, and one
timeline while it works. Read-only commands just run; anything that changes
something asks with a card right where the step is, and the card turns into the
step's record once you answer. It runs through
[panacea-claude-bridge](https://github.com/aphesist/panacea-claude-bridge) on a
Claude subscription.

<p>
<img src="docs/img/chat-idle.gif" width="400" alt="Empty island chat with the Claude logo and an animated orange pixel Claude">
<img src="docs/img/claude-chat.gif" width="400" alt="A question typed into the island chat: a read-only step runs on its own, then an approval card for mkdir is allowed and becomes a 'Run a command · Done' row above the reply">
</p>

### Tabs that slide

Switching Home ↔ Claude slides the page in from the side of the tab you picked,
and the tab pill stretches across. The model pills (Opus · Sonnet · Haiku) have
a selector that glides behind the names with a small overshoot.

<img src="docs/img/tabs.gif" width="400" alt="The island switching between Home and the Claude chat, then the model selector sliding between Opus, Sonnet and Haiku">

### Activity glow

A thin light runs along the island's exact outline, flares included, while
something works: Claude's orange while it thinks, white while the VPN connects,
and any agent's own colours (`panacea-glow start <name> "#hex,#hex"`, or
`panacea-glow run <name> "#hex" -- <command>`). It eases in and out with a springy stretch, fades out
towards the two ends where the island meets the screen, and moves with the
island as one piece. Settings → Motion → *Activity glow*: on/off per source, loop or bounce,
speed, intensity.

<img src="docs/img/glow.gif" width="680" alt="The collapsed island with a thin glow running along its edge: orange for Claude, then white, then violet and cyan for an agent">

### Mullvad, in the island

Left-click the island's country button for a Mullvad page in the island's own
style: status with a power button, every country and city (search, recents),
and Mullvad's settings (lockdown, LAN, quantum, DAITA, DNS blocking) as
toggles. Right-click still toggles the VPN. No more "VPN disconnected" piles of
notifications. *Change VPN client* goes back to Panacea's client picker.

<img src="docs/img/mullvad.gif" width="400" alt="The Mullvad page in the island switching from São Paulo to Stockholm and back (addresses masked)">

### Task manager

`Super+Shift+Esc`, like Windows, in the island's style. **Processes**: apps
grouped with their child processes and icons, then background and system
processes; right-click for End task, Force kill, Copy PID. **Performance**: this
machine's real parts (i9-13900H, LPDDR5 at its rated speed, Iris Xe and the RTX
4070, the NVMe, Wi-Fi, battery health) with live charts and per-thread bars; the
RTX is only read while it's already awake. **Services**: your user services,
with Start / Stop / Restart (system ones ask for your password).

<img src="docs/img/tasks.gif" width="820" alt="The task manager: the process tree with app icons, the Performance tab with CPU chart and thread bars, the Services list">

### One file picker, inside the island

The chat's paperclip, and Open/Save dialogs from every app (Zen, Claude
desktop, Electron and GTK apps, via an xdg-desktop-portal backend), morph the
island into its own file manager in picker mode, instead of a white GTK
window tiled behind it. If Panacea isn't running, apps fall back to the GTK
dialog on their own.

<img src="docs/img/picker.png" width="860" alt="Panacea's file manager in picker mode inside the island, with Cancel and Open buttons">

### Launcher and calendar

<p>
<img src="docs/img/launcher.png" width="420" alt="Panacea launcher">
<img src="docs/img/calendar.png" width="420" alt="Panacea calendar">
</p>

## What changes

| Area | Change | Where |
|---|---|---|
| **Lock screen** | Fingerprint unlock at any time, with no password first. A bare fingerprint glyph shows the state: pulses when ready, shakes on a miss, grows on success, dims when the reader is unavailable. A miss retries after 1.5 s | `hypr/custom/bin/lock-patch.py` |
| | Unlock fades into the desktop instead of cutting | `lock-patch.py` + `session_lock_xray` |
| | **Password once per boot**, like macOS after a restart: while the keyring is still locked, the lock screen asks for the password (which also unlocks the keyring through PAM) instead of the fingerprint. Every later unlock is fingerprint, and the keyring's white password prompt never appears | `lock-patch.py` |
| | Locked from the first frame: wallpaper and island are held back until the lock is confirmed, with a black `swaylock` fallback if it isn't up in 4 s | `autostart.lua`, `bin/after-lock` |
| | One lock entry point for startup, idle and lid; `flock` stops two lock clients from starting | `bin/panacea-lock` |
| **Idle** | On battery: lock at 5 min, screen off at 5.5, suspend at 15. Plugged in: lock at 10, screen off at 11 | `hypridle.conf`, `bin/idle-action` |
| **Vault** | Panacea's password manager becomes a front-end for **Proton Pass**: it shows logins from every vault, new and edited entries go back to Proton, and a delete only hides the entry. Offline, it falls back to the encrypted local copy | `panacea/scripts/custom/vault-proton.py`, `bin/vault-patch.py` |
| **Desktop** | Hides hyprpaper's splash quote for good: hyprpaper runs from its own config (`hyprpaper-conf`, written just before it starts from Panacea's saved wallpaper), so Panacea's login rewrite of `hyprpaper.conf` can't race it any more | `bin/hyprpaper-conf`, `systemd/user/panacea-wallpaper.service` |
| | **The wallpaper always comes back.** hyprpaper runs as its own service that restarts itself, so restarting or crashing the Panacea shell no longer leaves the desktop without a wallpaper (it used to be the shell's child) | `panacea-wallpaper.service`, `bin/after-lock` |
| | **Approval cards in Panacea's palette.** The island's approval toast had green ✓ / red × circles; now flat Deny / Allow pills (white = primary), matching the chat's approval card, and for Claude the pixel Claude itself, animated (it waves for your attention), centred on the card | `bin/portal-patch.py` |
| | **Mullvad from the island.** Panacea's VPN control could only drive Happ; any other client just opened its app. An adapter now drives the `mullvad` CLI: pick Mullvad in Choose VPN, then the island's country button and the VPN page's power button connect and disconnect it, and the island shows its real state. `mullvad/` has the setup that keeps the internet working whenever the VPN is off (systemd-resolved DNS, ufw kept, early-boot blocker off), a check script and a rescue script | `panacea/scripts/custom/mullvad_control.py`, `bin/vpn-patch.py`, `mullvad/` |
| | **Mullvad page in the island**: servers (countries, cities, search, recents) and settings as toggles; left-click opens it, right-click toggles; no notification spam | `bin/MullvadView.qml`, `bin/vpn-patch.py`, `bin/portal-patch.py` |
| | **Animated tabs**: Home ↔ Claude slides the page and stretches the tab pill | `bin/portal-patch.py` |
| | **Activity glow** along the island's outline while Claude thinks, the VPN connects or an agent runs; configurable in Settings → Motion; `panacea-glow` for scripts | `bin/IslandGlow.qml`, `bin/panacea-glow`, `bin/portal-patch.py` |
| | **Task manager** on **Super+Shift+Esc**: process tree with icons and End task, real hardware with live charts, user and system services | `bin/TasksView.qml`, `bin/TasksChart.qml`, `panacea/scripts/custom/taskman.py`, `keybindings.lua` |
| | **Password prompt in the island's style**: a plain lock, "Password needed" and one simple line saying what it's for ("Enter your password to run X as administrator"), polkit's raw text behind *Details*, flat Cancel / Unlock pills | `bin/auth-patch.py` |
| | Softer, slower island motion, closer to macOS: 440 ms, 18 % overshoot | `settings.overrides.json` |
| | Screenshot on **PrtSc** | `settings.overrides.json` |
| | Island chat on **Super+C** (Panacea has no shortcut for it) | `keybindings.lua` |
| | Voice dictation on **Right Ctrl** instead of AltGr, which Brazilian ABNT2 needs for `?` `/` `°` | `settings.overrides.json` |
| | Window corners 16 px with the same squircle curve as the island | `general.lua` |
| | **Three-finger swipe up/down = volume** (5 % per swipe, with the island's volume popup) instead of Panacea's fullscreen/close-window; sideways still switches workspaces | `bin/gesture-patch.py` |
| | Window resize moved to **Super+Alt+arrows**, so **Alt+←/→** reach apps again (back/forward in Zen) | Panacea Settings → Shortcuts (Panacea's own `binds_data.lua`, not in this repo) |
| | Touchpad right-click by pressing the bottom-right corner (as well as a two-finger tap), instead of Panacea's two-finger-press-only *clickfinger* | `general.lua` |
| | Spotify opens as a normal window (Panacea sends it to the hidden scratchpad) | `windowrules.lua` |
| **File picker** | One picker, inside the island. Every app's Open/Save dialog (browsers, Electron apps, GTK apps) and the chat's paperclip morph the island into its own file manager in picker mode, with Cancel/Open, a filename box for Save and "Use this folder" for folder picks. Before, apps got a white GTK dialog and the paperclip opened a window that Hyprland tiled behind the island. Falls back to the GTK dialog if Panacea can't answer | `bin/panacea-portal.py`, `bin/portal-patch.py`, `portal/` |
| **Spotify** | A Spicetify theme in Panacea's *Nothing* palette: pure black, white, one red; JetBrains Mono; rounded flat panels | `spicetify/Themes/Panacea` |
| | Runs natively on Wayland, so it follows the display scale (under XWayland with `force_zero_scaling` it was drawn at 1×, tiny); Vesktop (Discord) too | `spotify/spotify-flags.conf`, `electron/vesktop-flags.conf` |
| **Claude desktop** | Uses GNOME Keyring for its sign-in (Electron doesn't recognise Hyprland and fell back to "no keyring", so you had to sign in every launch) | `electron/claude-desktop-flags.conf` |
| | **Panacea theme** for the whole Claude desktop app, Chat included: pure black, white text, red as the only accent, every colour token set so nothing falls back to the stock blue/violet. Uses [claude-desktop-extra](https://github.com/patrickjaja/claude-desktop-extra) (the official app plus community patches; its build pulls Anthropic's signed `.deb`). With the official app, a Claude Code mod themes the Code tab instead | `claude-desktop/claude-desktop-extra.jsonc`, `claude-desktop/panacea-look` |
| **Zen Browser** | Web-content corners at 16 px instead of ~5, matching Hyprland's window rounding (`--zen-webview-border-radius`) | `zen/userChrome.css` |
| **Discord** | Vesktop made tiling-friendly: no minimum window size (Discord's 940 px didn't fit a half tile and got cut off), and none of Discord's own window buttons (close with Super+Q, like everything else) | `electron/vesktop-quickCss.css`, `install.sh` |
| **Display** | Internal 2880×1800 OLED at 120 Hz, scale 1.6. Change it for your panel | `monitors.lua` |
| **Terminal** | foot at size 11 to suit the 1.6 scale | `foot/custom.ini` |

The island chat → Claude integration is its own repo:
[panacea-claude-bridge](https://github.com/aphesist/panacea-claude-bridge).

## From a fresh Arch install

`setup.sh` rebuilds this whole machine on the **latest** versions: upstream
Panacea, then all four of my repos on top of it.

```sh
sudo pacman -S --needed git
git clone https://github.com/aphesist/panacea-config ~/src/panacea-config
bash ~/src/panacea-config/setup.sh
```

| Step | What it does |
|---|---|
| `repos` | Clones or updates `~/Panacea` from [EnsixD/Panacea](https://github.com/EnsixD/Panacea) and my repos into `~/src` |
| `panacea` | Panacea's own installer (packages, yay, configs, SDDM and GRUB themes) |
| `apps` | [arch-setup](https://github.com/aphesist/arch-setup) `apps/`: Zen, Spotify + Spicetify, Zed, Claude desktop, Figma, and the full dev toolchain |
| `nvidia` `camera` `fingerprint` | [galaxy-book3-ultra-linux](https://github.com/aphesist/galaxy-book3-ultra-linux). **Only on a Galaxy Book3 Ultra** (detected from DMI). The webcam driver is pinned to the reviewed commit |
| `config` | This repo's `install.sh` |
| `proton` | Proton Pass CLI and the browser login, for the vault sync |
| `claude` | Claude Code and the island chat bridge |
| `boot` → reboot → `autologin` | Silent boot, plus an *autologin test* GRUB entry. After you've tried the test entry, re-run the script to make autologin the default |

- **It asks before every step.** Answer `y`, `n` or `q`, or pass `--yes` to skip the questions.
- **It's resumable.** Progress is kept in `~/.local/state/panacea-setup`. `--list` shows it, and `--from <step>` redoes a step.
- **It never runs as root.** Root work goes through each repo's own scripts, run with `sudo`, and each script checks its own result.

## Install (Panacea already installed)

Install Panacea first, then:

```sh
git clone https://github.com/aphesist/panacea-config && cd panacea-config
bash install.sh
```

The installer backs up every file it replaces to
`~/.local/state/panacea-config/backup-<time>/`. It merges
`settings.overrides.json` into `~/.config/panacea/settings.json` rather than
overwriting it, then enables the user units and patches the lock screen.

**Optional pieces** each need one extra step:

| For | Do |
|---|---|
| Fingerprint on the lock screen | a working reader and the PAM file from [galaxy-book3-ultra-linux](https://github.com/aphesist/galaxy-book3-ultra-linux) → `fingerprint/2-lock-screen-pam.sh` |
| Proton Pass in the vault | `yay -S proton-pass-cli-bin`, then `pass-cli login` (the session key goes to GNOME Keyring, so it survives reboots) |
| Spotify theme | `yay -S spotify spicetify-cli`, `sudo chmod a+wr /opt/spotify /opt/spotify/Apps -R`, open Spotify once, then re-run `install.sh` |

## How patches survive updates

```
Panacea update replaces lock.qml / vault.sh / shell.qml
        │
        ├─ lock.qml   → bin/panacea-lock re-runs lock-patch.py before every lock
        ├─ vault.sh   → panacea-vault-patch.path notices the change → vault-patch.py
        └─ shell.qml, FilesView.qml → panacea-portal-patch.path → portal-patch.py
```

Each patcher searches for exact anchors in Panacea's code. If an update moved
them, the patcher **changes nothing** and Panacea's stock file keeps working.
You lose the extra, never the lock screen. `lock-patch.py` keeps
`lock.qml.pristine`, so a newer patch version upgrades cleanly.

### The vault, precisely

- **Unlock:** Panacea checks your password as before (PAM + its encrypted file). Then it lists your Proton Pass logins (`pass-cli item list --show-secrets`), minus the ones you hid.
- **Add:** the new entry is created in the *Personal* vault, with the password sent on stdin.
- **Edit:** only the changed fields go to `pass-cli item update`. That command takes values as arguments, so an edited password is briefly visible in your own process list.
- **Delete:** the entry is hidden in Panacea only. `pass-cli` can only delete permanently, so real deletion stays in the Proton apps, which have a trash.
- **Unencrypted on disk:** only item IDs (`~/.local/share/panacea/proton-*.json`). No secrets.

## Credits

[Panacea Shell](https://github.com/EnsixD/Panacea) by EnsixD (MIT). The patches
quote small parts of its QML in order to find their place.
[Proton Pass CLI](https://github.com/protonpass/pass-cli) by Proton AG (GPL-3.0),
used as an external program.
