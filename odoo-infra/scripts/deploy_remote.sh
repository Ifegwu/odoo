#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[odoo-infra] %s\n' "$1"
}

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required environment variable: $key" >&2
    exit 1
  fi
}

require_env "ODOO_DOMAIN"
require_env "ODOO_LETSENCRYPT_EMAIL"
require_env "ODOO_POSTGRES_USER"
require_env "ODOO_POSTGRES_PASSWORD"
require_env "ODOO_POSTGRES_DB"
require_env "ODOO_ADMIN_PASSWORD"

log "Validating DNS for ${ODOO_DOMAIN}"
if ! getent hosts "$ODOO_DOMAIN" >/dev/null 2>&1; then
  echo "Domain ${ODOO_DOMAIN} does not resolve (NXDOMAIN or missing DNS record)." >&2
  echo "Create an A/AAAA record for ${ODOO_DOMAIN} to this VM and rerun deployment." >&2
  exit 1
fi

DEPLOY_ROOT="/home/ubuntu/odoo-prod"
TMP_ROOT="/tmp/odoo-infra"
NGINX_TEMPLATE="$TMP_ROOT/nginx/odoo.conf.template"
COMPOSE_TEMPLATE="$TMP_ROOT/docker-compose.yml"

if [[ ! -f "$NGINX_TEMPLATE" || ! -f "$COMPOSE_TEMPLATE" ]]; then
  echo "Required deployment templates not found in $TMP_ROOT" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

log "Installing base dependencies"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release ufw nginx certbot python3-certbot-nginx

if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
fi

if ! docker compose version >/dev/null 2>&1; then
  log "Installing Docker Compose plugin"
  sudo apt-get install -y docker-compose-plugin
fi

log "Ensuring services are enabled"
sudo systemctl enable --now docker
sudo systemctl enable --now nginx

log "Configuring firewall rules"
sudo ufw allow OpenSSH || true
sudo ufw allow 80/tcp || true
sudo ufw allow 443/tcp || true
if sudo ufw status | grep -q "Status: inactive"; then
  yes | sudo ufw enable
fi

log "Preparing deploy directory"
mkdir -p "$DEPLOY_ROOT"

log "Writing environment file"
cat > "$DEPLOY_ROOT/.env" <<EOF
ODOO_DOMAIN=${ODOO_DOMAIN}
ODOO_LETSENCRYPT_EMAIL=${ODOO_LETSENCRYPT_EMAIL}
ODOO_POSTGRES_USER=${ODOO_POSTGRES_USER}
ODOO_POSTGRES_PASSWORD=${ODOO_POSTGRES_PASSWORD}
ODOO_POSTGRES_DB=${ODOO_POSTGRES_DB}
ODOO_ADMIN_PASSWORD=${ODOO_ADMIN_PASSWORD}
EOF
chmod 600 "$DEPLOY_ROOT/.env"

log "Installing compose file"
cp "$COMPOSE_TEMPLATE" "$DEPLOY_ROOT/docker-compose.yml"

log "Starting Odoo stack"
cd "$DEPLOY_ROOT"
sudo docker compose pull
sudo docker compose up -d --remove-orphans

log "Configuring nginx site"
sudo cp "$NGINX_TEMPLATE" /etc/nginx/sites-available/odoo
sudo sed -i "s/__ODOO_DOMAIN__/${ODOO_DOMAIN}/g" /etc/nginx/sites-available/odoo
sudo ln -sfn /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/odoo

sudo nginx -t
sudo systemctl reload nginx

log "Issuing/renewing TLS certificate"
sudo certbot --nginx \
  --non-interactive \
  --agree-tos \
  --redirect \
  --keep-until-expiring \
  --email "$ODOO_LETSENCRYPT_EMAIL" \
  -d "$ODOO_DOMAIN"

log "Final status"
sudo docker compose ps
curl --proto '=https' --tlsv1.2 -fsS -I --max-time 20 "https://${ODOO_DOMAIN}" >/dev/null
log "Deployment completed successfully: https://${ODOO_DOMAIN}"

