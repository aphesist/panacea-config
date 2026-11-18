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
Everything here lives in those folders. Two Panacea files are patched in place,
the lock screen and the vault script. Their patchers are idempotent,
all-or-nothing, and re-run themselves whenever an update replaces the file.

## Screenshots

### Claude in the island

A single agent tab with model pills; Enter sends. It runs through
[panacea-claude-bridge](https://github.com/aphesist/panacea-claude-bridge) on a
Claude subscription.

<img src="docs/img/chat.png" width="460" alt="Island chat patched into a single Claude tab with Opus, Sonnet and Haiku pills">

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
| | Locked from the first frame: wallpaper and island are held back until the lock is confirmed, with a black `swaylock` fallback if it isn't up in 4 s | `autostart.lua`, `bin/after-lock` |
| | One lock entry point for startup, idle and lid; `flock` stops two lock clients from starting | `bin/panacea-lock` |
| **Idle** | On battery: lock at 5 min, screen off at 5.5, suspend at 15. Plugged in: lock at 10, screen off at 11 | `hypridle.conf`, `bin/idle-action` |
| **Vault** | Panacea's password manager becomes a front-end for **Proton Pass**: it shows logins from every vault, new and edited entries go back to Proton, and a delete only hides the entry. Offline, it falls back to the encrypted local copy | `panacea/scripts/custom/vault-proton.py`, `bin/vault-patch.py` |
| **Desktop** | Hides hyprpaper's splash quote ("Configration"…): hyprpaper 0.8.5 ignores `splash = false`, so set `splash_opacity = 0` instead | `bin/hyprpaper-nosplash` + `.path` unit |
| | Softer, slower island motion, closer to macOS: 440 ms, 18 % overshoot | `settings.overrides.json` |
| | Screenshot on **PrtSc** | `settings.overrides.json` |
| | Window corners 16 px with the same squircle curve as the island | `general.lua` |
| | Spotify opens as a normal window (Panacea sends it to the hidden scratchpad) | `windowrules.lua` |
| **Spotify** | A Spicetify theme in Panacea's *Nothing* palette: pure black, white, one red; JetBrains Mono; rounded flat panels | `spicetify/Themes/Panacea` |
| | Runs natively on Wayland, so it follows the display scale (under XWayland with `force_zero_scaling` it was drawn at 1×, tiny) | `spotify/spotify-flags.conf` |
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
Panacea update replaces lock.qml / vault.sh
        │
        ├─ lock.qml  → bin/panacea-lock re-runs lock-patch.py before every lock
        └─ vault.sh  → panacea-vault-patch.path notices the change → vault-patch.py
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
