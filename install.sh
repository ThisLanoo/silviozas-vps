#!/bin/bash
# SilviozasbyLano VPS Installer
# Usage: bash install.sh
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[*]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[X]${NC} $1"; exit 1; }

echo ""
echo "=================================="
echo " SilviozasbyLano VPS Installer"
echo "=================================="
echo ""

# cek root
[ "$EUID" -ne 0 ] && err "Jalankan sebagai root: sudo bash install.sh"

# detect IP
VPS_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
log "VPS IP: $VPS_IP"

# --- 1. update & install ---
log "[1/6] Update system..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    openssl ufw curl screen

# --- 2. firewall ---
log "[2/6] Setup firewall..."
ufw allow 22/tcp   comment 'SSH'    > /dev/null
ufw allow 443/tcp  comment 'Auth'   > /dev/null
ufw allow 33131/tcp comment 'Proxy' > /dev/null
ufw --force enable > /dev/null
log "Firewall: SSH(22), Auth(443), Backend(33131) dibuka"

# --- 3. auth server ---
log "[3/6] Install auth server..."
mkdir -p /opt/silviozas-auth
cp "$(dirname "$0")/auth/app.py" /opt/silviozas-auth/app.py
python3 -m venv /opt/silviozas-auth/venv
/opt/silviozas-auth/venv/bin/pip install -q flask gunicorn

# generate SSL cert
openssl req -x509 -newkey rsa:4096 \
    -keyout /opt/silviozas-auth/key.pem \
    -out    /opt/silviozas-auth/cert.pem \
    -days 3650 -nodes \
    -subj "/CN=$VPS_IP" 2>/dev/null
log "SSL cert generated"

# init database
cd /opt/silviozas-auth
venv/bin/python3 -c "from app import init_db; init_db()"
log "Database initialized"

# --- 4. backend server ---
log "[4/6] Install backend server..."
mkdir -p /opt/silviozas-backend
cp "$(dirname "$0")/backend/server.py" /opt/silviozas-backend/server.py

# config files default
for f in gt_host gt_port overlay console; do
    [ ! -f "/opt/silviozas-backend/$f.txt" ] && \
    cp "$(dirname "$0")/backend/config/$f.txt" /opt/silviozas-backend/$f.txt
done

# --- 5. systemd services ---
log "[5/6] Setup services..."

# generate secret key random
SECRET=$(openssl rand -hex 24)

cat > /etc/systemd/system/silv-auth.service << EOF
[Unit]
Description=SilviozasbyLano Auth Server
After=network.target

[Service]
User=root
WorkingDirectory=/opt/silviozas-auth
Environment="ADMIN_SECRET=$SECRET"
ExecStart=/opt/silviozas-auth/venv/bin/gunicorn \\
    --workers 2 \\
    --bind 0.0.0.0:443 \\
    --certfile /opt/silviozas-auth/cert.pem \\
    --keyfile  /opt/silviozas-auth/key.pem \\
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/silv-backend.service << EOF
[Unit]
Description=SilviozasbyLano Backend Server
After=network.target

[Service]
User=root
WorkingDirectory=/opt/silviozas-backend
ExecStart=/usr/bin/python3 /opt/silviozas-backend/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable silv-auth silv-backend > /dev/null
systemctl start silv-backend
systemctl start silv-auth

# --- 6. simpan info penting ---
log "[6/6] Saving config..."
cat > /root/silviozas-info.txt << EOF
=== SilviozasbyLano VPS Info ===

VPS IP       : $VPS_IP
Auth Server  : https://$VPS_IP:443
Backend      : $VPS_IP:33131

ADMIN SECRET : $SECRET
(simpan ini baik-baik, dipakai untuk tambah/hapus user)

=== Tambah User Whitelist ===
curl -k -X POST https://$VPS_IP:443/api/adduser \\
  -d 'secret=$SECRET&username=NAMA&password=PASS&role=Premium Proxy User'

=== Hapus User ===
curl -k -X POST https://$VPS_IP:443/api/deluser \\
  -d 'secret=$SECRET&username=NAMA'

=== List Semua User ===
curl -k -X POST https://$VPS_IP:443/api/listusers \\
  -d 'secret=$SECRET'

=== Edit Config Backend ===
nano /opt/silviozas-backend/gt_host.txt    <- IP GT server
nano /opt/silviozas-backend/overlay.txt   <- pesan overlay
nano /opt/silviozas-backend/console.txt   <- pesan console

=== Proxy Client Config ===
auth.h:
  AUTH_HOST = L"$VPS_IP"
  AUTH_PATH = L"/api/verify"

backend_client.h:
  BACKEND_HOST = "$VPS_IP"

=== Update Config Backend (tanpa restart) ===
Edit file txt di /opt/silviozas-backend/ — server baca live
EOF

echo ""
echo "================================================"
echo -e " ${GREEN}SETUP SELESAI!${NC}"
echo "================================================"
echo ""
cat /root/silviozas-info.txt
echo ""
echo " File info disimpan di: /root/silviozas-info.txt"
echo ""
