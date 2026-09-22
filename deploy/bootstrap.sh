#!/usr/bin/env bash
# Idempotent DigitalOcean droplet bootstrap for ACIU Odoo 19.
# Invoked by GitHub Actions over SSH (see .github/workflows/deploy-odoo.yml).
# Safe to re-run.
set -euo pipefail

DEPLOY_PATH="${ODOO_DEPLOY_PATH:-/opt/odoo/odoo}"
SERVICE="${ODOO_SERVICE:-odoo}"
DB_NAME="${ODOO_DB_NAME:-aciu}"
DB_USER="${ODOO_DB_USER:-odoo}"
DB_PASSWORD="${ODOO_DB_PASSWORD:?ODOO_DB_PASSWORD is required}"
ADMIN_PASSWD="${ODOO_ADMIN_PASSWD:?ODOO_ADMIN_PASSWD is required}"
REPO_URL="${REPO_URL:-https://github.com/Ifegwu/odoo.git}"
GIT_BRANCH="${GIT_BRANCH:-production}"
CLONE_TOKEN="${GH_CLONE_TOKEN:-}"
HTTP_PORT="${ODOO_HTTP_PORT:-8069}"

export DEBIAN_FRONTEND=noninteractive

echo "==> Bootstrap host=$(hostname) path=${DEPLOY_PATH} db=${DB_NAME}"

echo "==> Ensure swap (1GB droplets often OOM during pip/odoo install)"
if ! swapon --show | grep -q .; then
  if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile || true
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Apt packages"
apt-get update -y
apt-get install -y \
  git curl wget build-essential \
  python3 python3-pip python3-venv python3-dev \
  libxml2-dev libxslt1-dev libevent-dev libsasl2-dev \
  libldap2-dev libpq-dev libjpeg-dev libpng-dev zlib1g-dev \
  libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev \
  libfribidi-dev libxcb1-dev \
  postgresql postgresql-contrib \
  libpq5 fonts-liberation \
  npm ufw

# wkhtmltopdf is optional for PDF reports; install if available
apt-get install -y wkhtmltopdf || echo "WARN: wkhtmltopdf not installed"

echo "==> System user odoo"
if ! id odoo >/dev/null 2>&1; then
  adduser --system --home /opt/odoo --group --shell /bin/bash odoo
fi
mkdir -p /opt/odoo /var/lib/odoo /var/log/odoo /etc/odoo
chown -R odoo:odoo /opt/odoo /var/lib/odoo /var/log/odoo

echo "==> PostgreSQL role + database"
systemctl enable --now postgresql
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH CREATEDB PASSWORD '${DB_PASSWORD}';"
# Keep password in sync with GitHub secret (also required for localhost auth)
sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH CREATEDB PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"

# Allow password auth over TCP localhost (avoid Unix-socket "peer" failures)
PG_HBA="$(sudo -u postgres psql -tAc 'SHOW hba_file')"
if [ -n "${PG_HBA}" ] && [ -f "${PG_HBA}" ]; then
  if ! grep -qE '^host\s+all\s+all\s+127\.0\.0\.1/32' "${PG_HBA}"; then
    echo "host all all 127.0.0.1/32 scram-sha-256" >> "${PG_HBA}"
  fi
  if ! grep -qE '^host\s+all\s+all\s+::1/128' "${PG_HBA}"; then
    echo "host all all ::1/128 scram-sha-256" >> "${PG_HBA}"
  fi
  systemctl reload postgresql || systemctl restart postgresql
fi

echo "==> Clone / update repository (shallow — full Odoo history is too large for small droplets)"
AUTH_URL="${REPO_URL}"
if [ -n "${CLONE_TOKEN}" ]; then
  AUTH_URL="$(echo "${REPO_URL}" | sed -E "s#https://#https://x-access-token:${CLONE_TOKEN}@#")"
fi
export GIT_TERMINAL_PROMPT=0

force_shallow_clone() {
  local url="$1"
  echo "==> Shallow clone ${GIT_BRANCH} → ${DEPLOY_PATH}"
  rm -rf "${DEPLOY_PATH}"
  sudo -u odoo git clone --depth 1 --branch "${GIT_BRANCH}" --single-branch "${url}" "${DEPLOY_PATH}"
}

sync_checkout() {
  local url="$1"
  # Incomplete or dirty tree from interrupted clones → wipe
  if [ -d "${DEPLOY_PATH}" ] && [ ! -d "${DEPLOY_PATH}/.git" ]; then
    echo "==> Removing incomplete checkout (no .git)"
    rm -rf "${DEPLOY_PATH}"
  fi

  if [ ! -d "${DEPLOY_PATH}/.git" ]; then
    force_shallow_clone "${url}"
    return
  fi

  cd "${DEPLOY_PATH}"
  sudo -u odoo git remote set-url origin "${url}"
  sudo -u odoo git fetch --depth 1 --prune origin "${GIT_BRANCH}" || sudo -u odoo git fetch --prune origin
  sudo -u odoo git clean -fd -e venv -e .venv || true

  if sudo -u odoo git checkout -f "${GIT_BRANCH}" 2>/dev/null \
    || sudo -u odoo git checkout -f -B "${GIT_BRANCH}" "origin/${GIT_BRANCH}" 2>/dev/null; then
    sudo -u odoo git reset --hard "origin/${GIT_BRANCH}" || sudo -u odoo git reset --hard "FETCH_HEAD"
  else
    echo "==> Dirty/broken git tree — wiping and re-cloning"
    cd /
    force_shallow_clone "${url}"
  fi
}

sync_checkout "${AUTH_URL}"

# Avoid leaving token in remote URL
cd "${DEPLOY_PATH}"
sudo -u odoo git remote set-url origin "${REPO_URL}"

echo "==> Python venv + requirements"
if [ ! -d "${DEPLOY_PATH}/venv" ]; then
  sudo -u odoo python3 -m venv "${DEPLOY_PATH}/venv"
fi
sudo -u odoo "${DEPLOY_PATH}/venv/bin/pip" install --upgrade pip wheel setuptools
sudo -u odoo "${DEPLOY_PATH}/venv/bin/pip" install -r "${DEPLOY_PATH}/requirements.txt"

echo "==> /etc/odoo/odoo.conf"
# Use localhost + password (not Unix socket peer auth) so OS user odoo
# can connect even when DB role name differs or peer is misconfigured.
cat > /etc/odoo/odoo.conf <<EOF
[options]
admin_passwd = ${ADMIN_PASSWD}
db_host = localhost
db_port = 5432
db_user = ${DB_USER}
db_password = ${DB_PASSWORD}
db_name = ${DB_NAME}
addons_path = ${DEPLOY_PATH}/addons,${DEPLOY_PATH}/odoo/addons,${DEPLOY_PATH}/custom_addons
data_dir = /var/lib/odoo
logfile = /var/log/odoo/odoo.log
http_port = ${HTTP_PORT}
proxy_mode = True
without_demo = all
list_db = False
EOF
chown root:odoo /etc/odoo/odoo.conf
chmod 640 /etc/odoo/odoo.conf

echo "==> systemd unit ${SERVICE}.service"
cat > "/etc/systemd/system/${SERVICE}.service" <<EOF
[Unit]
Description=ACIU Odoo 19
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=odoo
Group=odoo
WorkingDirectory=${DEPLOY_PATH}
ExecStart=${DEPLOY_PATH}/venv/bin/python ${DEPLOY_PATH}/odoo-bin -c /etc/odoo/odoo.conf
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable "${SERVICE}"

echo "==> Firewall (SSH + Odoo HTTP)"
ufw allow OpenSSH || true
ufw allow "${HTTP_PORT}/tcp" || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true

MARKER=/var/lib/odoo/.aciu_db_initialized
if [ ! -f "${MARKER}" ]; then
  echo "==> First-time DB init (-i ACIU modules)"
  systemctl stop "${SERVICE}" || true
  sudo -u odoo "${DEPLOY_PATH}/venv/bin/python" "${DEPLOY_PATH}/odoo-bin" \
    -c /etc/odoo/odoo.conf -d "${DB_NAME}" \
    -i base,aciu_base,aciu_membership,aciu_dues \
    --stop-after-init
  touch "${MARKER}"
  chown odoo:odoo "${MARKER}"
else
  echo "==> DB already initialized (marker ${MARKER})"
fi

systemctl restart "${SERVICE}"
sleep 3
systemctl --no-pager --full status "${SERVICE}" | head -n 25 || true

echo "==> Bootstrap finished"
echo "    URL: http://$(curl -fsS ifconfig.me 2>/dev/null || echo HOST):${HTTP_PORT}"
