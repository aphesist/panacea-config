#!/usr/bin/python3 -I
"""Native-messaging host for the "Panacea for Zen" add-on (Zen starts it).

Bridges a private unix socket ($XDG_RUNTIME_DIR/panacea-zen.sock, mode 0600) to the
add-on: each line a client writes is one JSON request ({"cmd": ...}); the answer comes
back as one JSON line. Clients: the panacea-zen command (used by the island)."""
import itertools, json, os, socket, struct, sys, threading

SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}", "panacea-zen.sock")
out_lock = threading.Lock()
pending = {}
ids = itertools.count(1)


def to_ext(msg):
    data = json.dumps(msg).encode()
    with out_lock:
        sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
        sys.stdout.buffer.flush()


def from_ext():
    while True:
        head = sys.stdin.buffer.read(4)
        if len(head) < 4:            # Zen closed us
            try: os.unlink(SOCK)
            except OSError: pass
            os._exit(0)
        msg = json.loads(sys.stdin.buffer.read(struct.unpack("<I", head)[0]))
        cb = pending.pop(msg.get("id"), None)
        if cb: cb(msg)


def serve(conn):
    with conn, conn.makefile("rwb") as f:
        for line in f:
            try: req = json.loads(line)
            except ValueError: continue
            if not isinstance(req, dict): continue
            i = next(ids); done = threading.Event(); box = {}
            pending[i] = lambda m, box=box, done=done: (box.update(m), done.set())
            req["id"] = i
            to_ext(req)
            if not done.wait(5):
                pending.pop(i, None); box = {"id": i, "error": "timeout"}
            box.pop("id", None)
            f.write((json.dumps(box) + "\n").encode()); f.flush()


def main():
    threading.Thread(target=from_ext, daemon=True).start()
    try: os.unlink(SOCK)
    except OSError: pass
    old = os.umask(0o177)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK)
    os.umask(old)
    srv.listen(8)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=serve, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
