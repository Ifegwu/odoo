#!/usr/bin/env bash
# Idempotent Nginx reverse proxy + Let's Encrypt for ACIU Odoo.
# Invoked by bootstrap.sh / deploy.sh (and GitHub Actions over SSH).
#
# Reproducible: nginx site is always rendered from deploy/nginx/*.template
# Certificates: certbot certonly --webroot (not certbot --nginx site mutation).
set -euo pipefail

DOMAIN="${ODOO_DOMAIN:-erp.aciugermany.online}"
EMAIL="${ODOO_LETSENCRYPT_EMAIL:-}"
DEPLOY_PATH="${ODOO_DEPLOY_PATH:-/opt/odoo/odoo}"
SERVICE="${ODOO_SERVICE:-odoo}"
HTTP_PORT="${ODOO_HTTP_PORT:-8069}"

if [ -z "${ODOO_DB_NAME:-}" ] && [ -f /etc/odoo/odoo.conf ]; then
  ODOO_DB_NAME="$(awk -F'=' '/^[[:space:]]*db_name[[:space:]]*=/ {gsub(/[[:space:]]/,"",$2); print $2; exit}' /etc/odoo/odoo.conf || true)"
fi
DB_NAME="${ODOO_DB_NAME:-odoo_prod}"

BASE_URL="https://${DOMAIN}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolve_template() {
  local name="$1"
  if [ -f "${SCRIPT_DIR}/nginx/${name}" ]; then
    echo "${SCRIPT_DIR}/nginx/${name}"
  elif [ -f "/tmp/nginx/${name}" ]; then
    echo "/tmp/nginx/${name}"
  else
    echo "ERROR: template nginx/${name} not found under ${SCRIPT_DIR} or /tmp" >&2
    exit 1
  fi
}

HTTPS_TEMPLATE="$(resolve_template odoo.conf.template)"
HTTP_TEMPLATE="$(resolve_template odoo.http-only.conf.template)"
SITE_AVAILABLE="/etc/nginx/sites-available/odoo"
SITE_ENABLED="/etc/nginx/sites-enabled/odoo"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
WEBROOT="/var/www/certbot"

log() { printf '[configure_tls] %s\n' "$*"; }

render_site() {
  local template="$1"
  sed "s|__ODOO_DOMAIN__|${DOMAIN}|g" "${template}" > "${SITE_AVAILABLE}"
  rm -f /etc/nginx/sites-enabled/default
  ln -sfn "${SITE_AVAILABLE}" "${SITE_ENABLED}"
  nginx -t
  systemctl reload nginx
}

if [ -z "${EMAIL}" ]; then
  echo "ERROR: ODOO_LETSENCRYPT_EMAIL is required for Certbot." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

log "Domain=${DOMAIN} email=${EMAIL} db=${DB_NAME}"

log "Validating DNS for ${DOMAIN}"
RESOLVED_IP="$(getent ahostsv4 "${DOMAIN}" 2>/dev/null | awk '{print $1; exit}' || true)"
PUBLIC_IP="$(curl -fsS --max-time 10 ifconfig.me 2>/dev/null || curl -fsS --max-time 10 icanhazip.com 2>/dev/null || true)"
PUBLIC_IP="$(echo "${PUBLIC_IP}" | tr -d '[:space:]')"

if [ -z "${RESOLVED_IP}" ]; then
  echo "ERROR: ${DOMAIN} does not resolve. Create Namecheap A record Host=erp → droplet IP and rerun." >&2
  exit 1
fi

if [ -n "${PUBLIC_IP}" ] && [ "${RESOLVED_IP}" != "${PUBLIC_IP}" ]; then
  echo "ERROR: ${DOMAIN} → ${RESOLVED_IP} but this host is ${PUBLIC_IP}. Fix DNS and rerun." >&2
  exit 1
fi

log "DNS OK: ${DOMAIN} → ${RESOLVED_IP}"

if ! command -v nginx >/dev/null 2>&1 || ! command -v certbot >/dev/null 2>&1; then
  log "Installing nginx + certbot"
  apt-get update -y
  apt-get install -y nginx certbot python3-certbot-nginx
else
  log "nginx + certbot already installed"
fi

systemctl enable --now nginx
mkdir -p "${WEBROOT}"

log "Firewall: SSH + 80/443"
ufw allow OpenSSH || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true

if [ ! -f "${CERT_PATH}" ]; then
  log "No certificate yet — HTTP-only site for ACME challenge"
  render_site "${HTTP_TEMPLATE}"

  log "Issuing Let's Encrypt certificate (webroot)"
  certbot certonly \
    --webroot -w "${WEBROOT}" \
    --non-interactive \
    --agree-tos \
    --email "${EMAIL}" \
    -d "${DOMAIN}"
else
  log "Certificate exists — renew if due"
  certbot renew --webroot -w "${WEBROOT}" --quiet || true
fi

# Ensure ssl-dhparams exists (certbot usually creates this)
if [ ! -f /etc/letsencrypt/ssl-dhparams.pem ]; then
  if [ -f /usr/share/doc/certbot/examples/ssl-dhparams.pem ]; then
    cp /usr/share/doc/certbot/examples/ssl-dhparams.pem /etc/letsencrypt/ssl-dhparams.pem
  else
    openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048
  fi
fi

# options-ssl-nginx.conf is installed by python3-certbot-nginx
if [ ! -f /etc/letsencrypt/options-ssl-nginx.conf ]; then
  cat > /etc/letsencrypt/options-ssl-nginx.conf <<'EOF'
ssl_session_cache shared:le_nginx_SSL:10m;
ssl_session_timeout 1440m;
ssl_session_tickets off;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";
EOF
fi

log "Rendering reproducible HTTPS nginx site from template"
render_site "${HTTPS_TEMPLATE}"

if [ -f /etc/odoo/odoo.conf ]; then
  if grep -qE '^[[:space:]]*http_interface[[:space:]]*=' /etc/odoo/odoo.conf; then
    sed -i -E "s|^[[:space:]]*http_interface[[:space:]]*=.*|http_interface = 127.0.0.1|" /etc/odoo/odoo.conf
  else
    printf '\nhttp_interface = 127.0.0.1\n' >> /etc/odoo/odoo.conf
  fi
  if grep -qE '^[[:space:]]*proxy_mode[[:space:]]*=' /etc/odoo/odoo.conf; then
    sed -i -E "s|^[[:space:]]*proxy_mode[[:space:]]*=.*|proxy_mode = True|" /etc/odoo/odoo.conf
  else
    printf 'proxy_mode = True\n' >> /etc/odoo/odoo.conf
  fi
  systemctl restart "${SERVICE}" || true
  ufw delete allow "${HTTP_PORT}/tcp" 2>/dev/null || true
fi

log "Setting Odoo web.base.url → ${BASE_URL}"
if sudo -u postgres psql -d "${DB_NAME}" -tAc "SELECT to_regclass('public.ir_config_parameter')" 2>/dev/null | grep -q ir_config_parameter; then
  sudo -u postgres psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<SQL
UPDATE ir_config_parameter
SET value = '${BASE_URL}', write_date = NOW()
WHERE key = 'web.base.url';

INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
SELECT 'web.base.url', '${BASE_URL}', 1, 1, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM ir_config_parameter WHERE key = 'web.base.url');

UPDATE ir_config_parameter
SET value = 'True', write_date = NOW()
WHERE key = 'web.base.url.freeze';

INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
SELECT 'web.base.url.freeze', 'True', 1, 1, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM ir_config_parameter WHERE key = 'web.base.url.freeze');
SQL
else
  log "WARN: ir_config_parameter missing — DB not initialized yet; base URL set on next run"
fi

log "Health check ${BASE_URL}/web/login"
for i in $(seq 1 15); do
  CODE="$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 15 "${BASE_URL}/web/login" || true)"
  if [[ "${CODE}" =~ ^(200|303|302)$ ]]; then
    log "OK: ${BASE_URL}/web/login (HTTP ${CODE})"
    break
  fi
  log "Waiting for HTTPS login... (${i}/15, last=${CODE})"
  [ "${i}" -eq 15 ] && echo "WARN: HTTPS login not reachable yet" >&2
  sleep 4
done

log "Finished: ${BASE_URL}"
# silence unused var warning for shellcheck-style readers
: "${DEPLOY_PATH}"
