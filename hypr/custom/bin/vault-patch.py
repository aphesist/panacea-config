#!/usr/bin/env python3
"""Hook Panacea's scripts/vault.sh into the Proton Pass bridge
(scripts/custom/vault-proton.py). Idempotent; re-run by panacea-vault-patch.path
when Panacea updates replace vault.sh. If the anchor is gone, nothing changes."""
import os, sys
F = os.path.expanduser("~/.config/panacea/scripts/vault.sh")
TAG = "# panacea-local vault patch v1"
ANCHOR = "\nset -u\n"
HOOK = (ANCHOR + TAG + ": hand off to the Proton Pass bridge\n"
        'if [ -z "${PANACEA_VAULT_ORIG:-}" ] && [ -x "$HOME/.config/panacea/scripts/custom/vault-proton.py" ]; then\n'
        '    exec "$HOME/.config/panacea/scripts/custom/vault-proton.py" "$@"\n'
        "fi\n")
s = open(F).read()
if TAG in s:
    sys.exit(0)
if s.count(ANCHOR) != 1:
    print("vault-patch: anchor not found - untouched", file=sys.stderr); sys.exit(2)
tmp = F + ".patch-tmp"
open(tmp, "w").write(s.replace(ANCHOR, HOOK, 1)); os.chmod(tmp, os.stat(F).st_mode); os.replace(tmp, F)
print("vault-patch: applied v1")
