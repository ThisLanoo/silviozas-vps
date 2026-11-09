"""
SilviozasbyLano Backend Server
Port 33131, raw TCP, XOR crypto sama persis dengan C++ server source
Config dibaca live dari file txt — edit tanpa restart
"""
import socket, threading, struct, random, time, os

HOST      = "0.0.0.0"
PORT      = 33131
BASE      = os.path.dirname(os.path.abspath(__file__))

def cfg(name: str, default: str = "") -> str:
    try:
        with open(os.path.join(BASE, f"{name}.txt")) as f:
            return f.read().strip()
    except:
        return default

# ── XOR crypto ───────────────────────────────────────────────────

def silv_xor(data: bytearray) -> bytearray:
    if len(data) < 32:
        return data
    key  = [data[4], data[5], data[6], data[7]]
    size = struct.unpack_from("<i", data, 28)[0]
    for i in range(8, 28):
        if i < len(data):
            data[i] ^= key[i % 4]
    end = 32 + max(size, 0)
    if end > len(data): end = len(data)
    for i in range(32, end):
        data[i] ^= key[i % 4]
    return data

def build_packet(text: str) -> bytes:
    tb   = text.encode()
    tlen = len(tb)
    size = 3 + tlen
    d    = bytearray(33 + size)
    d[0] = 4
    d[4] = random.randint(1, 255)
    d[5] = random.randint(1, 255)
    d[6] = random.randint(1, 255)
    d[7] = random.randint(1, 255)
    struct.pack_into("<i", d, 8,  1)
    struct.pack_into("<i", d, 28, size)
    d[32]       = 1
    d[33]       = tlen & 0xFF
    d[34]       = (tlen >> 8) & 0xFF
    d[35:35+tlen] = tb
    return bytes(silv_xor(d))

def decode_packet(data: bytes) -> str:
    if len(data) < 36 or data[0] != 4:
        return ""
    buf  = bytearray(data)
    silv_xor(buf)
    size = struct.unpack_from("<i", buf, 28)[0]
    if size < 3 or 32 + size > len(buf):
        return ""
    tlen = buf[33] | (buf[34] << 8)
    off  = 35
    if off + tlen > len(buf):
        tlen = len(buf) - off
    return buf[off:off+tlen].decode(errors="replace")

# ── client handling ───────────────────────────────────────────────

clients      = []
clients_lock = threading.Lock()

def send_safe(conn, text: str) -> bool:
    try:
        conn.sendall(build_packet(text))
        return True
    except:
        return False

def handle_client(conn: socket.socket, addr):
    print(f"[+] {addr} connected")
    with clients_lock:
        clients.append(conn)
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break
            msg = decode_packet(data)
            if not msg:
                continue
            print(f"[<] {addr}: {msg[:100]}")

            if msg.startswith("[GetServerData]"):
                resp = (
                    f"[ServerData]\n"
                    f"maint|{cfg('maint','0')}\n"
                    f"server|{cfg('gt_host','213.179.209.168')}\n"
                    f"port|{cfg('gt_port','17091')}\n"
                )
                send_safe(conn, resp)

            elif msg.startswith("[GetMeta]"):
                send_safe(conn, "[Meta]\nversion|1.0.0\nname|SilviozasbyLano\n")

            elif msg.startswith("[OnNewLogin]"):
                print(f"[LOGIN] {msg}")

            elif msg.startswith("[OnModDetect]"):
                path = os.path.join(BASE, "hdnmods.txt")
                with open(path, "a") as f:
                    f.write(msg + "\n---\n")
                print(f"[MOD] Logged to hdnmods.txt")

            elif msg.startswith("[OnGiveMods]"):
                path = os.path.join(BASE, "hdnmods.txt")
                try:
                    with open(path) as f:
                        mods = f.read()
                except:
                    mods = "Tidak ada hidden mod terdeteksi."
                send_safe(conn, "[HiddenMods]\n" + mods)

    except Exception as e:
        print(f"[-] {addr} error: {e}")
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print(f"[-] {addr} disconnected")

# ── broadcast loop ────────────────────────────────────────────────

def broadcast_loop():
    last_overlay = last_console = time.time()
    while True:
        time.sleep(5)
        now = time.time()
        with clients_lock:
            dead = []
            for c in clients:
                try:
                    if now - last_overlay >= 600:   # 10 menit
                        ov = cfg("overlay", "[SilviozasbyLano] Welcome!")
                        if not send_safe(c, "[OVERLAY]\n" + ov):
                            dead.append(c)
                    if now - last_console >= 60:    # 60 detik
                        cm = cfg("console", "SilviozasbyLano Backend Online")
                        if not send_safe(c, "[PROXYCONSOLE]\n" + cm):
                            dead.append(c)
                except:
                    dead.append(c)
            for d in dead:
                if d in clients: clients.remove(d)
        if now - last_overlay >= 600: last_overlay = now
        if now - last_console >= 60:  last_console = now

# ── main ──────────────────────────────────────────────────────────

def main():
    # buat config default kalau belum ada
    defaults = {
        "gt_host":  "213.179.209.168",
        "gt_port":  "17091",
        "maint":    "0",
        "overlay":  "[SilviozasbyLano] Welcome to SilviozasbyLano Premium Proxy!",
        "console":  "SilviozasbyLano Backend Online. Enjoy!",
    }
    for name, val in defaults.items():
        path = os.path.join(BASE, f"{name}.txt")
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(val)

    threading.Thread(target=broadcast_loop, daemon=True).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(64)
    print(f"[*] SilviozasbyLano Backend listening on {HOST}:{PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
