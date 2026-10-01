# Part of ACIU Odoo customization.
"""
Upsert ACIU members from Central IC Update PDF export JSON.

Usage (odoo-bin shell):
  ./odoo-bin shell -c /etc/odoo/odoo.conf -d odoo_prod --no-http < \\
    custom_addons/aciu_membership/scripts/import_ic_members.py

Expects JSON at:
  custom_addons/aciu_membership/data/aciu_ic_members_2026-09.json
"""

import json
import re
from pathlib import Path

JSON_PATH = Path(__file__).resolve().parents[1] / 'data' / 'aciu_ic_members_2026-09.json'

TITLE_RE = re.compile(
    r'^(CHIEF|MR\.?|MRS\.?|MS\.?|MAZI|PRINCE|PASTOR|ELDER|EVANG\.?|'
    r'DEAC\.?|ENG\.?|EZE)\s+',
    re.I,
)


def normalize_name(name: str) -> str:
    n = (name or '').upper()
    n = n.replace('\u2060', '')
    n = re.sub(r'\s*\(RETIRED\)\s*', ' ', n, flags=re.I)
    n = TITLE_RE.sub('', n)
    n = n.replace('.', ' ')
    n = re.sub(r'\s+', ' ', n).strip()
    # collapse duplicated title leftovers e.g. "MR MR DIKE"
    n = TITLE_RE.sub('', n).strip()
    return n


def display_name(name: str) -> str:
    """Human-readable contact name from IC sheet text."""
    n = re.sub(r'\s+', ' ', (name or '').replace('\u2060', '')).strip()
    n = re.sub(r'(?i)\bMR\.?\s+MR\.?\s+', 'Mr ', n)
    n = n.title()
    # Keep short initials readable: "J.J." / "O."
    n = re.sub(r'\b([A-Z])\b', lambda m: m.group(1).upper(), n)
    return n


def token_set(name_key: str) -> set[str]:
    return {t for t in name_key.split() if len(t) > 1}


def best_match(name_key: str, candidates: dict):
    """candidates: name_key -> partner recordset singleton."""
    if name_key in candidates:
        return candidates[name_key], 'exact'
    tokens = token_set(name_key)
    if len(tokens) < 3:
        return None, None
    best = None
    best_score = 0
    for key, partner in candidates.items():
        other = token_set(key)
        if len(other) < 2:
            continue
        inter = tokens & other
        # Require nearly-full containment of the shorter token set
        shorter, longer = (tokens, other) if len(tokens) <= len(other) else (other, tokens)
        if not shorter:
            continue
        if inter != shorter:
            continue
        # Avoid merging distinct people who share first+middle only
        if len(longer - shorter) > 1:
            continue
        score = len(inter)
        if score > best_score:
            best_score = score
            best = partner
    if best:
        return best, 'fuzzy'
    return None, None


data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
Company = env['res.company'].sudo()
Partner = env['res.partner'].sudo()

companies = {
    c.name: c
    for c in Company.search([('is_aciu_company', '=', True)])
}

# Build existing member index
existing = Partner.search([('is_aciu_member', '=', True)])
by_key = {}
by_key_all = {}
for p in existing:
    key = normalize_name(p.name or '')
    if not key:
        continue
    by_key_all.setdefault(key, p)
    if p.aciu_branch_id:
        by_key.setdefault(p.aciu_branch_id.id, {})[key] = p

created = updated = skipped = 0
report = []

for branch_key, rows in data.items():
    if not rows:
        continue
    erp_name = rows[0]['erp_branch']
    company = companies.get(erp_name)
    if not company:
        report.append(f'MISSING COMPANY: {erp_name}')
        continue
    branch_index = by_key.setdefault(company.id, {})
    for row in rows:
        name = display_name(row['name'])
        key = normalize_name(name)
        if not key:
            skipped += 1
            continue
        retired = bool(row.get('retired'))
        status = 'inactive' if retired else 'active'

        partner = None
        how = None
        if key in branch_index:
            partner, how = branch_index[key], 'exact-branch'
        else:
            partner, how = best_match(key, branch_index)
            if partner:
                how = f'{how}-branch'
        if not partner:
            # unique global match by exact key
            partner = by_key_all.get(key)
            if partner:
                how = 'exact-global'

        vals = {
            'name': name,
            'is_aciu_member': True,
            'aciu_branch_id': company.id,
            'aciu_membership_status': status,
            'company_id': False,
            'type': 'contact',
            'is_company': False,
            'country_id': env.ref('base.de').id,
        }

        if partner:
            # Preserve a more specific existing name if fuzzy matched and shorter/longer clash
            if how.startswith('fuzzy') and partner.name and len(partner.name) > len(name):
                vals.pop('name', None)
            partner.write(vals)
            updated += 1
            branch_index[key] = partner
            by_key_all[key] = partner
            report.append(f'UPDATE {erp_name}: {partner.name} ({how})')
        else:
            partner = Partner.create(vals)
            created += 1
            branch_index[key] = partner
            by_key_all[key] = partner
            report.append(f'CREATE {erp_name}: {partner.name}')

env.cr.commit()

# Summary counts
print('=== IMPORT DONE ===')
print(f'created={created} updated={updated} skipped={skipped}')
for c in Company.search([('is_aciu_company', '=', True)], order='name'):
    n = Partner.search_count([
        ('is_aciu_member', '=', True),
        ('aciu_branch_id', '=', c.id),
    ])
    if c.aciu_branch_code == 'DE-CENTRAL':
        continue
    print(f'  {c.name}: {n}')
print('TOTAL members', Partner.search_count([('is_aciu_member', '=', True)]))
