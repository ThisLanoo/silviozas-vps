"""
SilviozasbyLano Auth Server
Flask + SQLite whitelist
POST /api/verify  → body: username=X&password=Y
                  → resp: OK:<username>|<role>  atau  FAIL:<reason>
"""
from flask import Flask, request
import sqlite3, hashlib, os

app      = Flask(__name__)
DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")
SECRET   = os.environ.get("ADMIN_SECRET", "changeme")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'Premium Proxy User',
            active   INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def check_secret(req) -> bool:
    return req.form.get("secret","") == SECRET

# ── public endpoints ──────────────────────────────────────────────

@app.route("/api/verify", methods=["POST"])
def verify():
    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    if not username or not password:
        return "FAIL:Username atau password kosong"
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=? AND active=1",
        (username, hash_pw(password))
    ).fetchone()
    conn.close()
    if row:
        return f"OK:{row['username']}|{row['role']}"
    return "FAIL:User tidak ditemukan atau tidak diwhitelist. Beli proxy untuk akses."

@app.route("/api/version", methods=["GET"])
def version():
    return "1.0.0"

# ── admin endpoints (butuh secret) ───────────────────────────────

@app.route("/api/adduser", methods=["POST"])
def add_user():
    if not check_secret(request):
        return "FAIL:Unauthorized", 403
    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    role     = request.form.get("role","Premium Proxy User").strip()
    if not username or not password:
        return "FAIL:Data tidak lengkap"
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            (username, hash_pw(password), role)
        )
        conn.commit()
        conn.close()
        return f"OK:User {username} ditambahkan"
    except sqlite3.IntegrityError:
        return "FAIL:Username sudah ada"

@app.route("/api/deluser", methods=["POST"])
def del_user():
    if not check_secret(request):
        return "FAIL:Unauthorized", 403
    username = request.form.get("username","").strip()
    conn = get_db()
    conn.execute("UPDATE users SET active=0 WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return f"OK:User {username} dinonaktifkan"

@app.route("/api/listusers", methods=["POST"])
def list_users():
    if not check_secret(request):
        return "FAIL:Unauthorized", 403
    conn = get_db()
    rows = conn.execute(
        "SELECT username, role, active FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    if not rows:
        return "Tidak ada user"
    return "\n".join(
        f"{r['username']}|{r['role']}|{'aktif' if r['active'] else 'nonaktif'}"
        for r in rows
    )

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
