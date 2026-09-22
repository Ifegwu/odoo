# Deploy ACIU Odoo to DigitalOcean (automated)

Executed by GitHub Actions against Environment **`production`**:

- [`deploy/bootstrap.sh`](../../deploy/bootstrap.sh)
- [`deploy/deploy.sh`](../../deploy/deploy.sh)
- [`.github/workflows/deploy-odoo.yml`](../../.github/workflows/deploy-odoo.yml)

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
| `DROPLET_HOST` | `46.101.132.8` |
| `DROPLET_USER` | `root` |
| `DROPLET_SSH_KEY` | Private key PEM (`~/.ssh/erpkey`, no passphrase for CI) |
| `ODOO_DB_PASSWORD` or `ODOO_POSTGRES_PASSWORD` | Postgres password |
| `ODOO_ADMIN_PASSWD` or `ODOO_ADMIN_PASSWORD` | Odoo master `admin_passwd` (bootstrap) |

### Optional

| Secret | Default |
|--------|---------|
| `ODOO_DEPLOY_PATH` | `/opt/odoo/odoo` |
| `ODOO_SERVICE` | `odoo` |
| `ODOO_DB_NAME` or `ODOO_POSTGRES_DB` | `aciu` |
| `ODOO_DB_USER` or `ODOO_POSTGRES_USER` | `odoo` |
| `GH_CLONE_TOKEN` | GitHub PAT (repo read) for clone/fetch on droplet |
| `REPO_URL` | `https://github.com/Ifegwu/odoo.git` |

```bash
gh secret set DROPLET_HOST --env production --body '46.101.132.8'
gh secret set DROPLET_USER --env production --body 'root'
gh secret set DROPLET_SSH_KEY --env production < ~/.ssh/erpkey
gh secret set ODOO_DB_PASSWORD --env production --body '…'
gh secret set ODOO_ADMIN_PASSWD --env production --body '…'
gh secret set GH_CLONE_TOKEN --env production --body 'ghp_…'
```

Do **not** use or rely on `ORACLE_*` names for this pipeline.

Local key: `~/.ssh/erpkey` — never commit it.

---

## Networking

| Address | Use |
|---------|-----|
| **Public** `46.101.132.8` | GitHub Actions + browser |

---

## First-time (new droplet)

1. Public key in droplet `authorized_keys`.
2. Push `production` with `deploy/` + workflow.
3. Set secrets above.
4. **Run workflow → `bootstrap_and_deploy`**.
5. Open `http://46.101.132.8:8069`.

---

## Ongoing

Push to `production` or **Run workflow → `deploy`**.

---

## Security

- No real passwords/keys in git.
- Secrets only in GitHub Environment **production**.
- Passphrase-free deploy key for CI.
