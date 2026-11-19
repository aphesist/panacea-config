"""Mullvad adapter for Panacea's VPN control (panacea-local, see vpn-patch.py).

Panacea's vpn.py calls status() for `client-status` and toggle() for
`client-toggle` when the chosen VPN client is Mullvad. Both talk to the
Mullvad daemon through its CLI, so the island's country button and the VPN
page's power button connect and disconnect Mullvad directly.

States reported to the shell: connected, disconnected, busy (connecting or
disconnecting), blocked (Mullvad wants to be connected but can't, e.g. while
Wi-Fi reconnects after a resume; traffic is held back so nothing leaks).
"""
import json, shutil, subprocess, time

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
        out["relay"] = loc.get("hostname", "")
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
