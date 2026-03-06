# Homelable

A self-hosted, open-source tool to visually map, document and monitor your homelab infrastructure.

Interactive network canvas where each node is a physical machine, VM, LXC container, switch, or device. Nodes show live status, IPs, hostnames, and running services. Edges represent network links.

---

## Features

- **Interactive canvas** — drag, zoom, pan, snap-to-grid (React Flow)
- **11 node types** — ISP, router, switch, server, Proxmox, VM, LXC, NAS, IoT, AP, generic
- **5 edge types** — ethernet, Wi-Fi, IoT, VLAN (color-coded), virtual
- **Live status** — per-node checks via ping / HTTP / HTTPS / SSH / TCP / Prometheus
- **Network scanner** — nmap-based discovery, approve/hide/ignore new devices
- **Auto-layout** — one-click Dagre hierarchical arrangement
- **Export** — download canvas as PNG
- **Dark theme** — neon accent colors, JetBrains Mono for technical values
- **Self-contained** — SQLite database, single config file, no cloud dependency

---

## Quick Start — Docker

```bash
git clone https://github.com/you/homelable.git
cd homelable

docker compose up -d
```

Open **http://localhost:3000** — login with `admin` / `admin`.

> Change the password before exposing to a network: edit `backend/config.yml` and replace `password_hash` with a new bcrypt hash.
>
> Generate a hash: `docker compose exec backend python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('yourpassword'))"`

---

## Quick Start — Development

**Backend (Python 3.13):**
```bash
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Default login: `admin` / `admin`

---

## Proxmox LXC Install

Run inside a Debian/Ubuntu LXC container:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/you/homelable/main/scripts/lxc-install.sh)
```

This installs the backend as a systemd service and serves the frontend via nginx.

---

## Configuration

`backend/config.yml`:

```yaml
auth:
  username: admin
  password_hash: "$2b$12$..."   # bcrypt hash

scanner:
  ranges:
    - "192.168.1.0/24"          # CIDR ranges to scan

status_checker:
  interval_seconds: 60          # how often to check node status
```

All settings are also editable in-app via the **Scan Network** button.

---

## Node Check Methods

| Method | Description |
|--------|-------------|
| `ping` | ICMP ping |
| `http` | GET request, success if status < 500 |
| `https` | GET with TLS verify |
| `tcp` | TCP connect (target: `host:port`) |
| `ssh` | TCP connect to port 22 |
| `prometheus` | GET `/metrics` |
| `health` | GET `/health` |

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, TypeScript, Vite, React Flow v12, Zustand, Tailwind CSS, Shadcn/ui |
| Backend | FastAPI, SQLAlchemy async, SQLite, APScheduler, python-nmap |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Deployment | Docker Compose, nginx, systemd |

---

## Development

```bash
# Backend tests
cd backend && source .venv/bin/activate
pytest                    # 40 tests

# Backend lint
ruff check .

# Frontend tests
cd frontend && npm test

# Frontend lint + typecheck
npm run lint && npm run typecheck
```
