"""Mullvad adapter for Panacea's VPN control (panacea-local, see vpn-patch.py).

Panacea's vpn.py calls status() for `client-status` and toggle() for
`client-toggle` when the chosen VPN client is Mullvad. Both talk to the
Mullvad daemon through its CLI, so the island's country button and the VPN
page's power button connect and disconnect Mullvad directly.

States reported to the shell: connected, disconnected, busy (connecting or
disconnecting), blocked (Mullvad wants to be connected but can't, e.g. while
Wi-Fi reconnects after a resume; traffic is held back so nothing leaks).
"""
import json, os, pathlib, re, shutil, subprocess, sys, time

STATES = {"connected": "connected", "disconnected": "disconnected",
          "connecting": "busy", "disconnecting": "busy", "error": "blocked"}


def _mullvad(*args, timeout=10):
    if not shutil.which("mullvad"):
        raise ValueError("Mullvad isn't installed (mullvad-vpn-bin)")
    r = subprocess.run(["mullvad", *args], text=True, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise ValueError((r.stderr or r.stdout).strip().splitlines()[0] if (r.stderr or r.stdout).strip()
                         else "The Mullvad daemon isn't responding")
    return r.stdout


def _raw():
    # retried: right after a connect/disconnect the daemon can be briefly busy
    for attempt in range(3):
        try:
            return json.loads(_mullvad("status", "--json"))
        except (ValueError, subprocess.TimeoutExpired):
            if attempt == 2:
                raise
            time.sleep(0.5)


def status():
    d = _raw()
    state = STATES.get(str(d.get("state", "")).lower(), "busy")
    out = {"clientState": state}
    loc = (d.get("details") or {}).get("location") or {}
    if state == "connected" and loc:
        out["country"] = loc.get("country", "")
        out["city"] = loc.get("city", "")
        out["relay"] = loc.get("hostname", "") or ""
        if out["relay"][2:3] == "-":                 # br-sao-wg-301 -> BR, for the island's button
            out["countryCode"] = out["relay"][:2].upper()
    return out


def toggle():
    # anything but "disconnected" (connected, connecting, blocked) means: turn it off
    going_up = _raw().get("state") == "disconnected"
    try:
        _mullvad("connect" if going_up else "disconnect", timeout=25)
    except (ValueError, subprocess.TimeoutExpired):
        pass   # judged by where the state ends up, below
    want = "connected" if going_up else "disconnected"
    deadline = time.time() + 20
    st = status()
    while st["clientState"] != want and time.time() < deadline:
        time.sleep(0.5)
        st = status()
    if st["clientState"] != want and not (going_up and st["clientState"] in ("busy", "blocked")):
        raise ValueError(f"Mullvad didn't {'connect' if going_up else 'disconnect'} (state: {st['clientState']})")
    return {"ok": True, "action": "up" if going_up else "down", **st}



# ------------------------------------------------------------------ the Mullvad page
# Run as a script by the island's Mullvad page (MullvadView.qml, written by vpn-patch.py):
#   state                      everything the page shows, one JSON object
#   relays                     countries and cities (cached for a day)
#   connect | disconnect | reconnect
#   location <cc> [city]       pick a server location (and connect, like the app does)
#   set <key> <on|off>         autoconnect lockdown lan quantum daita ads trackers malware adult gambling social
CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or pathlib.Path.home() / ".cache") / "panacea-mullvad"
DNS_KEYS = {"ads": "Block ads", "trackers": "Block trackers", "malware": "Block malware",
            "adult": "Block adult content", "gambling": "Block gambling", "social": "Block social media"}
DNS_FLAGS = {"ads": "--block-ads", "trackers": "--block-trackers", "malware": "--block-malware",
             "adult": "--block-adult-content", "gambling": "--block-gambling", "social": "--block-social-media"}


def _kv(text):
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _on(v):
    return str(v).strip().lower() in ("on", "true", "allow", "enabled", "yes")


def relays():
    f = CACHE / "relays.json"
    if f.exists() and time.time() - f.stat().st_mtime < 86400:
        try:
            return json.loads(f.read_text())
        except ValueError:
            pass
    countries, cur, city = [], None, None
    for line in _mullvad("relay", "list", timeout=20).splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(\S.*) \((\w+)\)$", line)
        if m:
            cur = {"code": m.group(2), "name": m.group(1), "cities": []}
            countries.append(cur)
            continue
        m = re.match(r"^\t(\S.*?) \((\w+)\) @", line)
        if m and cur is not None:
            city = {"code": m.group(2), "name": m.group(1), "count": 0}
            cur["cities"].append(city)
            continue
        if line.startswith("\t\t") and city is not None:
            city["count"] += 1
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(countries))
    return countries


def _recents():
    try:
        return json.loads((CACHE / "recents.json").read_text())[:5]
    except (OSError, ValueError):
        return []


def _remember(cc, city):
    items = [r for r in _recents() if not (r.get("cc") == cc and r.get("city") == city)]
    names = {c["code"]: c for c in relays()}
    country = names.get(cc, {"name": cc.upper(), "cities": []})
    label = next((c["name"] for c in country["cities"] if c["code"] == city), "") if city else ""
    items.insert(0, {"cc": cc, "city": city, "label": (label + ", " if label else "") + country["name"]})
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "recents.json").write_text(json.dumps(items[:5]))


def state():
    d = _raw()
    st = status()
    loc = (d.get("details") or {}).get("location") or {}
    out = dict(st)
    out["here"] = ", ".join(x for x in (loc.get("city"), loc.get("country")) if x)
    if st["clientState"] == "connected":
        out["ip"] = loc.get("ipv4") or ""
    rel = _kv(_mullvad("relay", "get"))
    m = re.match(r"(country|city|hostname)\s+(.*)", rel.get("Location", ""))
    sel = {"cc": "", "city": "", "host": ""}
    if m:
        parts = [x.strip() for x in m.group(2).split(",")]
        if m.group(1) == "country":
            sel["cc"] = parts[0]
        elif m.group(1) == "city":
            sel["city"], sel["cc"] = parts[0], parts[-1]
        else:
            sel["host"] = parts[0]; sel["cc"] = parts[0][:2]
    out["selected"] = sel
    dns = _kv(_mullvad("dns", "get"))
    out["dns"] = {k: _on(dns.get(v, "false")) for k, v in DNS_KEYS.items()}
    out["customDns"] = _on(dns.get("Custom DNS", "no"))
    tun = _kv(_mullvad("tunnel", "get"))
    out["quantum"] = _on(tun.get("Quantum resistance", "off"))
    out["daita"] = _on(tun.get("DAITA", "false"))
    out["lan"] = _on(_mullvad("lan", "get").rsplit(":", 1)[-1])
    out["lockdown"] = _on(_mullvad("lockdown-mode", "get").rsplit(":", 1)[-1])
    out["autoconnect"] = _on(_mullvad("auto-connect", "get").rsplit(":", 1)[-1])
    out["recents"] = _recents()
    if os.path.exists(os.path.expanduser("~/.cache/panacea-demo")):   # screenshots: no real addresses
        out["here"] = "your real location"
        if out.get("ip"):
            out["ip"] = "203.0.113.24"
    return out


def setting(key, value):
    v = "on" if _on(value) else "off"
    if key == "autoconnect":
        _mullvad("auto-connect", "set", v)
    elif key == "lockdown":
        _mullvad("lockdown-mode", "set", v)
    elif key == "lan":
        _mullvad("lan", "set", "allow" if v == "on" else "block")
    elif key == "quantum":
        _mullvad("tunnel", "set", "quantum-resistant", v)
    elif key == "daita":
        _mullvad("tunnel", "set", "daita", v)
    elif key in DNS_FLAGS:
        cur = _kv(_mullvad("dns", "get"))
        want = {k: _on(cur.get(n, "false")) for k, n in DNS_KEYS.items()}
        want[key] = v == "on"
        _mullvad("dns", "set", "default", *[DNS_FLAGS[k] for k, on in want.items() if on])
    else:
        raise ValueError("unknown setting: " + key)
    return {"ok": True}


def main(argv):
    cmd = argv[0] if argv else "state"
    if cmd == "state":
        return state()
    if cmd == "relays":
        return {"countries": relays()}
    if cmd in ("connect", "disconnect", "reconnect"):
        _mullvad(cmd, timeout=15)
        return {"ok": True}
    if cmd == "location" and len(argv) >= 2:
        cc, city = argv[1].lower(), (argv[2].lower() if len(argv) > 2 else "")
        if not re.fullmatch(r"[a-z]{2}", cc) or (city and not re.fullmatch(r"[a-z0-9]{2,5}", city)):
            raise ValueError("bad location")
        _mullvad("relay", "set", "location", cc, *([city] if city else []))
        _remember(cc, city)
        if _raw().get("state") == "disconnected":
            _mullvad("connect", timeout=15)
        return {"ok": True}
    if cmd == "set" and len(argv) == 3:
        return setting(argv[1], argv[2])
    raise ValueError("usage: state | relays | connect | disconnect | reconnect | location <cc> [city] | set <key> <on|off>")


if __name__ == "__main__":
    try:
        print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
    except Exception as e:  # the page shows this instead of a stack trace
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
