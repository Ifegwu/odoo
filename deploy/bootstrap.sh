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
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"

echo "==> Clone / update repository"
AUTH_URL="${REPO_URL}"
if [ -n "${CLONE_TOKEN}" ]; then
  # https://github.com/org/repo.git → https://x-access-token:TOKEN@github.com/org/repo.git
  AUTH_URL="$(echo "${REPO_URL}" | sed -E "s#https://#https://x-access-token:${CLONE_TOKEN}@#")"
fi

if [ ! -d "${DEPLOY_PATH}/.git" ]; then
  sudo -u odoo git clone --branch "${GIT_BRANCH}" --single-branch "${AUTH_URL}" "${DEPLOY_PATH}" \
    || {
      # Branch may not exist yet — clone default then checkout later
      sudo -u odoo git clone "${AUTH_URL}" "${DEPLOY_PATH}"
      cd "${DEPLOY_PATH}"
      sudo -u odoo git fetch origin "${GIT_BRANCH}:${GIT_BRANCH}" || true
      sudo -u odoo git checkout "${GIT_BRANCH}" || sudo -u odoo git checkout -b "${GIT_BRANCH}"
    }
else
  cd "${DEPLOY_PATH}"
  if [ -n "${CLONE_TOKEN}" ]; then
    sudo -u odoo git remote set-url origin "${AUTH_URL}"
  fi
  sudo -u odoo git fetch --prune origin
  sudo -u odoo git checkout "${GIT_BRANCH}" || sudo -u odoo git checkout -b "${GIT_BRANCH}" "origin/${GIT_BRANCH}"
  sudo -u odoo git reset --hard "origin/${GIT_BRANCH}" || true
fi

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
cat > /etc/odoo/odoo.conf <<EOF
[options]
admin_passwd = ${ADMIN_PASSWD}
db_host = False
db_port = False
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
