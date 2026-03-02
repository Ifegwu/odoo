# Odoo Local Run Guide (uv)

This guide installs and runs Odoo from this repository using `uv`.

## 1) Install system dependencies (one-time)

```bash
cd /home/agbanyim/workspace/odoo
sudo ./setup/debinstall.sh
sudo apt-get install -y build-essential python3-dev libldap2-dev libsasl2-dev libssl-dev libpq-dev
```

## 2) Install Python dependencies with uv (one-time)

```bash
cd /home/agbanyim/workspace/odoo
uv sync
```

## 3) Prepare PostgreSQL role and database (one-time)

```bash
sudo -u postgres createuser --createdb --login agbanyim
sudo -u postgres createdb -O agbanyim odoo_dev
```

If you get "already exists", continue.

## 4) Initialize database schema (one-time)

```bash
cd /home/agbanyim/workspace/odoo
uv run ./odoo-bin -d odoo_dev --db_user=agbanyim -i base --without-demo=all --stop-after-init
```

## 5) Run Odoo

```bash
cd /home/agbanyim/workspace/odoo
uv run ./odoo-bin -d odoo_dev --db_user=agbanyim --http-interface=127.0.0.1 --http-port=8069 --log-level=info
```

## 6) Login

Open:

- http://localhost:8069/web/login

Login credentials for a fresh local DB:

- Login: `admin`
- Password: `admin`

After first login, change the admin password.

## Daily start command

```bash
cd /home/agbanyim/workspace/odoo
uv run ./odoo-bin -d odoo_dev --db_user=agbanyim --http-interface=127.0.0.1 --http-port=8069 --log-level=info
```

