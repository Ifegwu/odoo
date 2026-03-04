# Odoo Infrastructure Automation

This directory contains deployment automation for running Odoo on the same
Oracle VM used for n8n, exposed via nginx and Let's Encrypt TLS.

## Target Domain

- `erp.healthmate.live` (configurable via `ODOO_DOMAIN`)

## Components

- Odoo container
- PostgreSQL container
- nginx reverse proxy virtual host
- certbot certificate provisioning/renewal

## Files

- `docker-compose.yml` - Odoo + PostgreSQL stack
- `nginx/odoo.conf.template` - nginx virtual host template
- `scripts/deploy_remote.sh` - idempotent server deployment script
- `env.example` - required variables

## GitHub Workflow

- `.github/workflows/odoo.yml`

This workflow:
1. Calculates config fingerprint for idempotent deploys.
2. Uploads `odoo-infra/` to the Oracle VM when needed.
3. Runs remote deployment script.
4. Verifies endpoint health with retries.
5. Collects diagnostics on failure.

## Required Secrets

- `ORACLE_HOST`
- `ORACLE_USER`
- `ORACLE_SSH_PRIVATE_KEY`
- `ODOO_DOMAIN`
- `ODOO_LETSENCRYPT_EMAIL`
- `ODOO_POSTGRES_USER`
- `ODOO_POSTGRES_PASSWORD`
- `ODOO_POSTGRES_DB`
- `ODOO_ADMIN_EMAIL`
- `ODOO_ADMIN_PASSWORD`

## PostgreSQL isolation from n8n

The Odoo deployment uses its own PostgreSQL container and Docker volume
(`odoo-postgres` + `odoo_pg_data`), so it does not reuse n8n's PostgreSQL data.

To avoid accidental overlap with shared naming, use dedicated Odoo values:

- `ODOO_POSTGRES_USER=odoo_prod`
- `ODOO_POSTGRES_DB=odoo_prod`
- a strong `ODOO_POSTGRES_PASSWORD` value distinct from n8n

