# Tortobaza deployment guide

Manual deployment of Tortobaza on an Ubuntu AWS instance.

## Overview

- Project lives at `/home/ubuntu/koding/tortobaza`
- Backend (Django + DRF, Poetry) runs on `127.0.0.1:8100` under `systemd`
- Frontend (Next.js production build) runs on `127.0.0.1:3100` under `systemd`
- Nginx (already installed and running on the host) reverse-proxies both services
- Two virtual hosts:
  - `dev.sweet-chill.ge` — **enabled** now
  - `sweet-chill.ge` — config provided but **kept disabled** until production is ready

Standard ports `80`/`443` are already used by nginx (which is fine), and ports `3000`/`8000` may be taken by other services on the host. The app therefore listens on non-standard ports `3100` and `8100` bound to loopback only — they are never exposed publicly, only nginx is.

| Component | Bind | Port |
| --- | --- | --- |
| Django backend | `127.0.0.1` | `8100` |
| Next.js frontend | `127.0.0.1` | `3100` |
| Nginx (public) | `0.0.0.0` | `80` / `443` |

---

## 1. Prerequisites on the AWS instance

SSH in as `ubuntu`, then install system dependencies. Nginx is already installed; do not reinstall it.

```bash
sudo apt update
sudo apt install -y git curl build-essential \
    python3.12 python3.12-venv python3.12-dev
```

Install Node.js 22 (LTS) for the Next.js production build:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

Install Poetry for the `ubuntu` user:

```bash
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
poetry --version
```

Configure Poetry to keep virtualenvs inside each project (makes the systemd unit deterministic):

```bash
poetry config virtualenvs.in-project true
```

---

## 2. Clone the repository

```bash
mkdir -p /home/ubuntu/koding
cd /home/ubuntu/koding
git clone <REPO_URL> tortobaza
cd tortobaza
```

The final layout must be exactly:

```
/home/ubuntu/koding/tortobaza
├── backend/
├── frontend/
└── DEPLOY.md
```

---

## 3. Backend setup

```bash
cd /home/ubuntu/koding/tortobaza/backend
poetry install --no-root
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
```

(Optional) seed demo catalog data:

```bash
poetry run python seed_demo.py
```

Smoke test before wiring `systemd`:

```bash
poetry run python manage.py runserver 127.0.0.1:8100
# Ctrl-C after `curl -s http://127.0.0.1:8100/health/` returns OK
```

> The current `backend/tortobaza/settings.py` ships with `DEBUG = True` and `ALLOWED_HOSTS = ["*"]`, which is acceptable for `dev.sweet-chill.ge`. Tighten both before enabling the production vhost.

---

## 4. Frontend setup

```bash
cd /home/ubuntu/koding/tortobaza/frontend
npm ci
```

Create `.env.local` so `next.config.ts` proxies `/api` and `/media` rewrites to the local Django process:

```bash
cat > /home/ubuntu/koding/tortobaza/frontend/.env.local <<'EOF'
BACKEND_ORIGIN=http://127.0.0.1:8100
EOF
```

Production build:

```bash
npm run build
```

Smoke test:

```bash
npm run start -- -H 127.0.0.1 -p 3100
# Ctrl-C after `curl -sI http://127.0.0.1:3100/` returns 200
```

---

## 5. Systemd services

Create both unit files as `root`.

### 5.1 Backend — `/etc/systemd/system/tortobaza-backend.service`

```ini
[Unit]
Description=Tortobaza Django backend (dev)
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/koding/tortobaza/backend
Environment=PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/.local/bin/poetry run python manage.py runserver 127.0.0.1:8100 --noreload
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5.2 Frontend — `/etc/systemd/system/tortobaza-frontend.service`

```ini
[Unit]
Description=Tortobaza Next.js frontend (dev)
After=network.target tortobaza-backend.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/koding/tortobaza/frontend
Environment=NODE_ENV=production
Environment=PORT=3100
Environment=HOSTNAME=127.0.0.1
Environment=BACKEND_ORIGIN=http://127.0.0.1:8100
ExecStart=/usr/bin/npm run start -- -H 127.0.0.1 -p 3100
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5.3 Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tortobaza-backend.service
sudo systemctl enable --now tortobaza-frontend.service
sudo systemctl status tortobaza-backend.service tortobaza-frontend.service --no-pager
```

Quick checks:

```bash
curl -s http://127.0.0.1:8100/health/
curl -sI http://127.0.0.1:3100/
```

---

## 6. Nginx

Two server blocks live in `sites-available/`. Only the dev one is symlinked into `sites-enabled/`.

### 6.1 Dev vhost — `/etc/nginx/sites-available/dev.sweet-chill.ge`

```nginx
upstream tortobaza_backend_dev  { server 127.0.0.1:8100; keepalive 16; }
upstream tortobaza_frontend_dev { server 127.0.0.1:3100; keepalive 16; }

server {
    listen 80;
    listen [::]:80;
    server_name dev.sweet-chill.ge;

    client_max_body_size 25m;

    access_log /var/log/nginx/dev.sweet-chill.ge.access.log;
    error_log  /var/log/nginx/dev.sweet-chill.ge.error.log;

    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header Upgrade           $http_upgrade;
    proxy_set_header Connection        "upgrade";
    proxy_read_timeout 60s;

    # Django: API, admin, health, static and uploaded media
    location /api/    { proxy_pass http://tortobaza_backend_dev; }
    location /admin/  { proxy_pass http://tortobaza_backend_dev; }
    location /health/ { proxy_pass http://tortobaza_backend_dev; }
    location /static/ { proxy_pass http://tortobaza_backend_dev; }
    location /media/  { proxy_pass http://tortobaza_backend_dev; }

    # Next.js for everything else (pages, _next/*, hot data fetches)
    location / {
        proxy_pass http://tortobaza_frontend_dev;
    }
}
```

Enable it:

```bash
sudo ln -sf /etc/nginx/sites-available/dev.sweet-chill.ge \
            /etc/nginx/sites-enabled/dev.sweet-chill.ge
sudo nginx -t
sudo systemctl reload nginx
```

### 6.2 Prod vhost (kept disabled) — `/etc/nginx/sites-available/sweet-chill.ge`

Same shape as the dev one, pointing at the same upstreams. **Do not symlink it into `sites-enabled/` yet.**

```nginx
upstream tortobaza_backend  { server 127.0.0.1:8100; keepalive 16; }
upstream tortobaza_frontend { server 127.0.0.1:3100; keepalive 16; }

server {
    listen 80;
    listen [::]:80;
    server_name sweet-chill.ge www.sweet-chill.ge;

    client_max_body_size 25m;

    access_log /var/log/nginx/sweet-chill.ge.access.log;
    error_log  /var/log/nginx/sweet-chill.ge.error.log;

    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header Upgrade           $http_upgrade;
    proxy_set_header Connection        "upgrade";
    proxy_read_timeout 60s;

    location /api/    { proxy_pass http://tortobaza_backend; }
    location /admin/  { proxy_pass http://tortobaza_backend; }
    location /health/ { proxy_pass http://tortobaza_backend; }
    location /static/ { proxy_pass http://tortobaza_backend; }
    location /media/  { proxy_pass http://tortobaza_backend; }

    location / {
        proxy_pass http://tortobaza_frontend;
    }
}
```

Just write the file; do **not** create the symlink in `sites-enabled/` yet.

```bash
ls /etc/nginx/sites-enabled/
# tortobaza must list ONLY dev.sweet-chill.ge (no sweet-chill.ge yet)
```

### 6.3 DNS

Point `dev.sweet-chill.ge` to the AWS instance public IP. Leave `sweet-chill.ge` and `www.sweet-chill.ge` for later.

---

## 7. HTTPS (recommended for the dev host)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d dev.sweet-chill.ge
sudo systemctl reload nginx
```

`certbot` will rewrite the dev server block to listen on `443` with the cert it just issued. Auto-renewal is wired up via the `certbot.timer` systemd unit.

---

## 8. Turning on production later

When `sweet-chill.ge` is ready:

1. Tighten Django:
   - `DEBUG = False`
   - `ALLOWED_HOSTS = ["sweet-chill.ge", "www.sweet-chill.ge", "dev.sweet-chill.ge"]`
   - Move `SECRET_KEY` out of source.
2. Symlink and reload nginx:

   ```bash
   sudo ln -sf /etc/nginx/sites-available/sweet-chill.ge \
               /etc/nginx/sites-enabled/sweet-chill.ge
   sudo nginx -t
   sudo systemctl reload nginx
   ```
3. Issue a cert:

   ```bash
   sudo certbot --nginx -d sweet-chill.ge -d www.sweet-chill.ge
   sudo systemctl reload nginx
   ```

---

## 9. Updating a deployed instance

```bash
cd /home/ubuntu/koding/tortobaza
git pull --ff-only

cd backend
poetry install --no-root
poetry run python manage.py migrate

cd ../frontend
npm ci
npm run build

sudo systemctl restart tortobaza-backend.service
sudo systemctl restart tortobaza-frontend.service
```

---

## 10. Operations cheatsheet

```bash
# Status
sudo systemctl status tortobaza-backend.service tortobaza-frontend.service --no-pager

# Logs (live)
sudo journalctl -u tortobaza-backend.service  -f
sudo journalctl -u tortobaza-frontend.service -f
sudo tail -f /var/log/nginx/dev.sweet-chill.ge.access.log \
             /var/log/nginx/dev.sweet-chill.ge.error.log

# Restart
sudo systemctl restart tortobaza-backend.service
sudo systemctl restart tortobaza-frontend.service

# Verify upstream binds
ss -ltnp | grep -E '8100|3100'

# Verify nginx config
sudo nginx -t
sudo systemctl reload nginx
```
