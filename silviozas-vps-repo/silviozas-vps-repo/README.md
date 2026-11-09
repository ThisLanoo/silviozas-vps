# SilviozasbyLano VPS Server

Backend + Auth server untuk SilviozasbyLano Premium Proxy.

## Install (Ubuntu 22.04)

```bash
git clone https://github.com/USERNAME/REPO-NAME.git
cd REPO-NAME
bash install.sh
```

Selesai. Semua info tersimpan di `/root/silviozas-info.txt`

## Struktur

```
install.sh              ← satu perintah setup semua
auth/
  app.py                ← Flask auth server (port 443 HTTPS)
backend/
  server.py             ← backend proxy server (port 33131)
  config/
    gt_host.txt         ← IP Growtopia server
    gt_port.txt         ← port Growtopia
    overlay.txt         ← pesan overlay in-game
    console.txt         ← pesan console broadcast
```

## Manage User

```bash
# tambah user
curl -k -X POST https://IP_VPS:443/api/adduser \
  -d 'secret=SECRET&username=lanoo&password=pass123&role=Premium Proxy User'

# hapus user
curl -k -X POST https://IP_VPS:443/api/deluser \
  -d 'secret=SECRET&username=lanoo'

# list semua user
curl -k -X POST https://IP_VPS:443/api/listusers \
  -d 'secret=SECRET'
```

## Edit Config Backend (tanpa restart)

```bash
nano /opt/silviozas-backend/gt_host.txt
nano /opt/silviozas-backend/overlay.txt
nano /opt/silviozas-backend/console.txt
```

## Cek Status Service

```bash
systemctl status silv-auth
systemctl status silv-backend
```
