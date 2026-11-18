#!/usr/bin/env python3
"""Panacea vault <-> Proton Pass (Proton Pass is the source of truth).

Called instead of scripts/vault.sh (patched by ~/.config/hypr/custom/bin/vault-patch.py),
with the same interface:
    load   stdin: password             stdout: JSON array [{id,label,login,pw,at,url}]
    save   stdin: password, then JSON
    wipe   (passed through to the original)
Exit codes: 0 ok, 1 error, 2 wrong password  (same as vault.sh)

load: verifies the password against Panacea's local encrypted file (original
      vault.sh), then returns your Proton Pass logins from every vault, minus
      the ones you hid in Panacea. If Proton is unreachable, the local copy.
save: new entries -> created in the default vault (password sent via stdin),
      changed entries -> updated, removed entries -> HIDDEN in Panacea only
      (pass-cli can only delete permanently; delete in the Proton apps instead).
      The list is also saved to Panacea's local encrypted file (offline copy).

Only IDs are stored unencrypted (map/hidden/loaded files); never secrets.
"""
import json, os, pathlib, shutil, subprocess, sys, time

HOME = pathlib.Path.home()
ORIG = HOME / ".config/panacea/scripts/vault.sh"
DATA = pathlib.Path(os.environ.get("PANACEA_VAULT_DATA", HOME / ".local/share/panacea"))
MAP = DATA / "proton-map.json"        # Panacea id -> "pp:<share>:<item>"
HIDDEN = DATA / "proton-hidden.json"  # pp ids hidden in Panacea
LOADED = DATA / "proton-loaded.json"  # pp ids shown at the last load
DEFAULT_VAULT = "Personal"

ENV = dict(os.environ, PROTON_PASS_LINUX_KEYRING="dbus", PROTON_PASS_DISABLE_TELEMETRY="1",
           PANACEA_VAULT_ORIG="1")


def jload(p, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def jsave(p, obj):
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj))
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def orig(action, stdin_text):
    r = subprocess.run(["bash", str(ORIG), action], input=stdin_text, capture_output=True,
                       text=True, env=ENV)
    return r.returncode, r.stdout


def pc(*args, stdin=None):
    if not shutil.which("pass-cli"):
        raise RuntimeError("pass-cli not installed")
    r = subprocess.run(["pass-cli", *args], input=stdin, capture_output=True, text=True,
                       env=ENV, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"pass-cli {args[0]} {args[1] if len(args) > 1 else ''}: "
                           + (r.stderr.strip().splitlines() or ["failed"])[-1])
    return r.stdout


def proton_logins():
    """{pp_id: {label, login, login_field, pw, url, at}} for all vaults."""
    out, vaults = {}, json.loads(pc("vault", "list", "--output", "json"))["vaults"]
    for v in vaults:
        items = json.loads(pc("item", "list", "--share-id", v["share_id"], "--filter-type", "login",
                              "--filter-state", "active", "--show-secrets", "--output", "json"))
        for it in items.get("items", []):
            c = it.get("content") or {}
            login = (c.get("content") or {}).get("Login") or {}
            user, email = login.get("username") or "", login.get("email") or ""
            mt = it.get("modify_time")
            try:
                at = time.strftime("%d.%m.%Y %H:%M", time.localtime(int(mt))) if mt else ""
            except (TypeError, ValueError):
                at = str(mt or "")
            out[f"pp:{it['share_id']}:{it['id']}"] = {
                "label": c.get("title") or it.get("title") or "",
                "login": user or email,
                "login_field": "username" if user or not email else "email",
                "pw": login.get("password") or "",
                "url": (login.get("urls") or [""])[0],
                "at": at,
            }
    return out, vaults


def do_load(pw):
    code, local = orig("load", pw + "\n")
    if code != 0:
        return code                                   # wrong password / error: same as before
    try:
        logins, _ = proton_logins()
    except Exception as e:
        print(f"vault-proton: Proton unreachable, using local copy ({e})", file=sys.stderr)
        sys.stdout.write(local)
        return 0
    hidden = set(jload(HIDDEN, []))
    entries = [{"id": pid, "label": d["label"], "login": d["login"], "pw": d["pw"],
                "at": d["at"], "url": d["url"]}
               for pid, d in logins.items() if pid not in hidden]
    entries.sort(key=lambda e: e["label"].lower())
    jsave(LOADED, [e["id"] for e in entries])
    sys.stdout.write(json.dumps(entries, ensure_ascii=False))
    return 0


def is_email(s):
    return "@" in s and " " not in s


def do_save(pw, body):
    entries = json.loads(body)
    if not isinstance(entries, list):
        return 1
    idmap, hidden, loaded = jload(MAP, {}), set(jload(HIDDEN, [])), set(jload(LOADED, []))
    try:
        logins, vaults = proton_logins()
    except Exception as e:                           # offline / not logged in / no pass-cli:
        print(f"vault-proton: Proton unreachable, saved locally only ({e})", file=sys.stderr)
        return orig("save", pw + "\n" + body)[0]     # new entries sync on the next online save
    share = next((v["share_id"] for v in vaults if v["name"] == DEFAULT_VAULT), vaults[0]["share_id"])

    present = set()
    for e in entries:
        pid = e["id"] if str(e.get("id", "")).startswith("pp:") else idmap.get(e.get("id"))
        if pid and pid in logins:                    # existing: update changed fields
            cur, fields = logins[pid], []
            if e.get("label", "") != cur["label"]:
                fields.append(f"title={e.get('label', '')}")
            if e.get("login", "") != cur["login"]:
                fields.append(f"{cur['login_field']}={e.get('login', '')}")
            if e.get("pw", "") != cur["pw"]:
                fields.append(f"password={e.get('pw', '')}")
            if fields:
                _, s, i = pid.split(":", 2)
                args = ["item", "update", "--share-id", s, "--item-id", i]
                for f in fields:
                    args += ["--field", f]
                pc(*args)
            present.add(pid)
        elif pid:                                    # mapped but gone from Proton: deleted there
            present.add(pid)
        else:                                        # new in Panacea: create in Proton
            login = e.get("login", "")
            tmpl = {"title": e.get("label") or "Untitled",
                    "username": None if is_email(login) else (login or None),
                    "email": login if is_email(login) else None,
                    "password": e.get("pw") or None, "totp_uri": None,
                    "urls": [e["url"]] if e.get("url") else [], "extra_fields": []}
            before = set(proton_logins()[0])
            pc("item", "create", "login", "--share-id", share, "--from-template", "-",
               stdin=json.dumps(tmpl))
            new = [p for p in proton_logins()[0] if p not in before]
            if len(new) == 1:
                idmap[e["id"]] = new[0]
                present.add(new[0])

    hidden |= (loaded - present)                     # removed in Panacea -> hide only
    jsave(MAP, idmap)
    jsave(HIDDEN, sorted(hidden))
    jsave(LOADED, sorted(present))
    code, _ = orig("save", pw + "\n" + json.dumps(entries, ensure_ascii=False))   # offline copy
    return code


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in ("load", "save"):
        os.execvpe("bash", ["bash", str(ORIG), *sys.argv[1:]], ENV)
    pw = sys.stdin.readline().rstrip("\n")
    try:
        return do_load(pw) if action == "load" else do_save(pw, sys.stdin.read())
    except Exception as e:
        print(f"vault-proton: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
