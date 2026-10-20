# Deploy ACIU Odoo to DigitalOcean (automated)

Executed by GitHub Actions against Environment **`production`**:

- [`deploy/bootstrap.sh`](../../deploy/bootstrap.sh)
- [`deploy/deploy.sh`](../../deploy/deploy.sh)
- [`deploy/configure_tls.sh`](../../deploy/configure_tls.sh)
- [`deploy/nginx/`](../../deploy/nginx/) — reproducible Nginx templates
- [`.github/workflows/deploy-odoo.yml`](../../.github/workflows/deploy-odoo.yml)

Public URL: **https://erp.aciugermany.online**

---

## Branch strategy

| Branch | Purpose | CI |
|--------|---------|-----|
| Feature branches | Work | No deploy |
| `19.0` | Integration | No deploy |
| **`production`** | Live droplet | Auto **deploy** on push |

Manual: **Actions → Deploy Odoo to DigitalOcean → Run workflow**  
Modes: `bootstrap` | `deploy` | `bootstrap_and_deploy`

---

## Environments

| Environment | Status | Used by workflow? |
|-------------|--------|-------------------|
| **`production`** | Exists | **Yes** |
| **`development`** | Not created | No |

Put secrets under **Settings → Environments → production → Environment secrets**.

---

## Required secrets (`production` env)

| Secret | Example / notes |
|--------|------------------|
| `DROPLET_HOST` | Droplet public IPv4 |
| `DROPLET_USER` | `root` |
| `DROPLET_SSH_KEY` | Private key PEM (`~/.ssh/erpkey`, no passphrase for CI) |
| `ODOO_DB_PASSWORD` or `ODOO_POSTGRES_PASSWORD` | Postgres password |
| `ODOO_ADMIN_PASSWD` or `ODOO_ADMIN_PASSWORD` | Odoo master `admin_passwd` (bootstrap) |
| `ODOO_LETSENCRYPT_EMAIL` | Contact email for Let's Encrypt (e.g. admin@aciugermany.online) |

### Optional

| Secret | Default |
|--------|---------|
| `ODOO_DOMAIN` | `erp.aciugermany.online` |
| `ODOO_DEPLOY_PATH` | `/opt/odoo/odoo` |
| `ODOO_SERVICE` | `odoo` |
| `ODOO_DB_NAME` or `ODOO_POSTGRES_DB` | `odoo_prod` |
| `ODOO_DB_USER` or `ODOO_POSTGRES_USER` | `odoo` |
| `GH_CLONE_TOKEN` | GitHub PAT (repo read) for clone/fetch on droplet |
| `REPO_URL` | `https://github.com/Ifegwu/odoo.git` |

```bash
gh secret set DROPLET_HOST --env production --body 'YOUR_DROPLET_IP'
gh secret set DROPLET_USER --env production --body 'root'
gh secret set DROPLET_SSH_KEY --env production < ~/.ssh/erpkey
gh secret set ODOO_DB_PASSWORD --env production --body '…'
gh secret set ODOO_ADMIN_PASSWD --env production --body '…'
gh secret set ODOO_LETSENCRYPT_EMAIL --env production --body 'admin@aciugermany.online'
gh secret set ODOO_DOMAIN --env production --body 'erp.aciugermany.online'   # optional
gh secret set GH_CLONE_TOKEN --env production --body 'ghp_…'
```

Do **not** use or rely on `ORACLE_*` names for this pipeline.

Local key: `~/.ssh/erpkey` — never commit it.

---

## DNS (Namecheap) — do this before TLS deploy

In **Advanced DNS**, add:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A Record | `erp` | Droplet public IPv4 | 5 min (during cutover) |

Leave apex `@` / `www` parking as-is unless you want those elsewhere.

Verify:

```bash
dig +short erp.aciugermany.online
# must equal the droplet IP
```

Also open **DigitalOcean Cloud Firewall** (and UFW is handled by scripts): TCP **80**, **443**, **22**.

---

## What CI configures on the droplet

1. **Nginx** reverse proxy — `server_name erp.aciugermany.online` from [`deploy/nginx/odoo.conf.template`](../../deploy/nginx/odoo.conf.template)
2. **Let's Encrypt** via `certbot certonly --webroot` (site file stays git-owned / reproducible)
3. **Odoo** `proxy_mode = True`, `http_interface = 127.0.0.1` (HTTPS only via Nginx)
4. **`web.base.url`** = `https://erp.aciugermany.online` (+ freeze)

Every deploy re-renders the Nginx site from the template and renews the cert if due.

---

## Networking

| Address | Use |
|---------|-----|
| **https://erp.aciugermany.online** | Users + CI health check |
| Droplet public IP | SSH / `DROPLET_HOST` only (not the app URL) |

---

## First-time (new droplet or first HTTPS cutover)

1. Namecheap A record `erp` → droplet IP; wait until `dig` matches.
2. Public key in droplet `authorized_keys`.
3. Push `production` with `deploy/` + workflow.
4. Set secrets above (including `ODOO_LETSENCRYPT_EMAIL`).
5. **Run workflow → `bootstrap_and_deploy`** (or `deploy` if Odoo already running).
6. Open **https://erp.aciugermany.online**.

---

## Ongoing

Push to `production` or **Run workflow → `deploy`**.

---

## Security

- No real passwords/keys in git.
- Secrets only in GitHub Environment **production**.
- Passphrase-free deploy key for CI.
- After TLS succeeds, Odoo listens on localhost only; public HTTP(S) is Nginx 80/443.
