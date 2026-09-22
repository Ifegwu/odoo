# ACIU custom addons

Custom Odoo 19 modules for Abiriba Communal Union (ACIU). Do **not** modify Odoo core under `addons/` or `odoo/`.

## Modules

| Module | Purpose |
|--------|---------|
| `aciu_base` | Companies (central + 11 DE branches), `is_registered_ev`, security groups |
| `aciu_membership` | Member profile on contacts, soft open-debt display |
| `aciu_dues` | €20 annual due product, per-branch roll-call fee, contribution helpers |

## Addons path

Point Odoo at this folder (in addition to core addons), for example:

```bash
./odoo-bin -d aciu --addons-path=addons,odoo/addons,custom_addons -i aciu_base,aciu_membership,aciu_dues
```

Or in `odoo.conf`:

```ini
addons_path = addons,odoo/addons,custom_addons
```

## Install order

1. `aciu_base`
2. `aciu_membership`
3. `aciu_dues`

Depends on: `base`, `contacts`, `account`, `product` (and transitively `l10n_de` when you load German CoA on companies).

## After install

1. Assign users to ACIU security groups (Member, Branch Leader, …) — not Settings / Admin.
2. Confirm Berlin-Brandenburg roll-call fee is €5; set other branches when known.
3. Load `l10n_de` chart on ACIU Germany and each branch company as needed.
4. Create bank journals per company for real accounts.

See `docs/aciu/ACIU-Odoo-PRD.md` for full requirements.

## Production deploy

Automated in CI — see [`docs/aciu/DEPLOY.md`](../docs/aciu/DEPLOY.md).

1. Push / merge to **`production`**
2. Or **Actions → Deploy Odoo to DigitalOcean** with mode `bootstrap` (new droplet) or `deploy`
