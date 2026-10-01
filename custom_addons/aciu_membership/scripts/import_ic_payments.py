# Part of ACIU Odoo customization.
"""
Import Central IC payment rows from parsed JSON into account.move invoices
on ACIU Germany (only company with sale/bank journals today).

JSON: /tmp/aciu_payments_from_pdf.json (or data/aciu_ic_payments_2026-09.json)

Invoice ref scheme:
  IC|DUES|2025|<partner_id>
  IC|DUES|2026|<partner_id>
  IC|ARU|<partner_id>
  IC|AMB|<partner_id>
"""

import json
import re
from pathlib import Path

JSON_CANDIDATES = [
    Path('/tmp/aciu_payments_from_pdf.json'),
    Path('/opt/odoo/odoo/custom_addons/aciu_membership/data/aciu_ic_payments_2026-09.json'),
]

TITLE_RE = re.compile(
    r'^(CHIEF|MR\.?|MRS\.?|MS\.?|MAZI|PRINCE|PASTOR|ELDER|EVANG\.?|'
    r'DEAC\.?|ENG\.?|EZE)\s+',
    re.I,
)


def normalize_name(name: str) -> str:
    n = (name or '').upper().replace('\u2060', '')
    n = re.sub(r'\s*\(RETIRED\)\s*', ' ', n, flags=re.I)
    n = TITLE_RE.sub('', n).replace('.', ' ')
    n = re.sub(r'\s+', ' ', n).strip()
    return TITLE_RE.sub('', n).strip()


def token_set(name_key: str) -> set[str]:
    return {t for t in name_key.split() if len(t) > 1}


def find_json():
    for p in JSON_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError('IC payments JSON not found')


def match_partner(Partner, branch_company, name, indexes):
    key = normalize_name(name)
    branch_idx, global_idx = indexes
    if key in branch_idx.get(branch_company.id, {}):
        return branch_idx[branch_company.id][key]
    # exact global
    if key in global_idx:
        return global_idx[key]
    # strict fuzzy within branch
    tokens = token_set(key)
    if len(tokens) >= 3:
        for ek, partner in branch_idx.get(branch_company.id, {}).items():
            other = token_set(ek)
            shorter, longer = (tokens, other) if len(tokens) <= len(other) else (other, tokens)
            if shorter and shorter <= longer and len(longer - shorter) <= 1:
                return partner
    return Partner.browse()


data = json.loads(find_json().read_text(encoding='utf-8'))
Company = env['res.company'].sudo()
Partner = env['res.partner'].sudo()
Move = env['account.move'].sudo()

central = Company.search([('aciu_branch_code', '=', 'DE-CENTRAL')], limit=1)
if not central:
    raise Exception('ACIU Germany central company missing')

companies = {c.name: c for c in Company.search([('is_aciu_company', '=', True)])}

product_due = env.ref('aciu_dues.product_aciu_annual_due')
product_aru = env.ref('aciu_dues.product_aciu_burial_levy')
product_amb = env.ref('aciu_dues.product_aciu_central_project')
for prod in (product_due, product_aru, product_amb):
    if prod.taxes_id or prod.supplier_taxes_id:
        prod.product_tmpl_id.write({'taxes_id': [(5,)], 'supplier_taxes_id': [(5,)]})

# Index members
members = Partner.search([('is_aciu_member', '=', True)])
branch_idx = {}
global_idx = {}
for p in members:
    key = normalize_name(p.name or '')
    if not key:
        continue
    global_idx.setdefault(key, p)
    if p.aciu_branch_id:
        branch_idx.setdefault(p.aciu_branch_id.id, {})[key] = p
indexes = (branch_idx, global_idx)

# Cancel non-IC draft customer invoices (pilot leftovers)
drafts = Move.search([
    ('move_type', '=', 'out_invoice'),
    ('state', '=', 'draft'),
    ('ref', 'not ilike', 'IC|%'),
])
cancelled_drafts = 0
for inv in drafts:
    try:
        inv.button_cancel()
        cancelled_drafts += 1
    except Exception:
        pass

created = paid_n = unpaid_n = skipped = missing_partner = 0
errors = []


def upsert_invoice(partner, ref, label, product, amount, mark_paid, invoice_date):
    global created, paid_n, unpaid_n, skipped
    if amount is None or amount <= 0:
        skipped += 1
        return
    existing = Move.search([
        ('ref', '=', ref),
        ('company_id', '=', central.id),
        ('move_type', '=', 'out_invoice'),
        ('state', '!=', 'cancel'),
    ], limit=1)
    move = existing
    if not move:
        move = Move.with_company(central).with_context(skip_computed_taxes=True).create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'company_id': central.id,
            'invoice_date': invoice_date,
            'ref': ref,
            'narration': f'Imported from ACIU Germany Central IC Update. Home branch: {partner.aciu_branch_id.display_name or "-"}',
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': label,
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [(5,)],
            })],
        })
        move.invoice_line_ids.with_context(skip_computed_taxes=True).write({'tax_ids': [(5,)]})
        created += 1
    if move.state == 'draft':
        move.action_post()
    if mark_paid and move.payment_state not in ('paid', 'in_payment', 'reversed'):
        wiz = env['account.payment.register'].with_company(central).with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).sudo().create({})
        wiz.action_create_payments()
        paid_n += 1
    elif not mark_paid:
        unpaid_n += 1


for branch_name, rows in data.items():
    branch = companies.get(branch_name)
    if not branch:
        errors.append(f'Missing company {branch_name}')
        continue
    for row in rows:
        partner = match_partner(Partner, branch, row['name'], indexes)
        if not partner:
            missing_partner += 1
            errors.append(f'No partner: {branch_name} / {row["name"]}')
            continue
        # Annual dues
        for year, key, date in (
            ('2025', 'dues_2025', '2025-01-01'),
            ('2026', 'dues_2026', '2026-01-01'),
        ):
            st = row[key]
            if st['status'] == 'none':
                continue
            upsert_invoice(
                partner,
                f'IC|DUES|{year}|{partner.id}',
                f'ACIU Annual Membership Due {year}',
                product_due,
                st.get('amount') or 20.0,
                st['status'] == 'paid',
                date,
            )
        # Aru levy
        aru = row['aru']
        if aru['status'] != 'none':
            amt = aru.get('paid_amount') or aru.get('balance') or 10.0
            if aru['status'] == 'partial':
                # unpaid remainder invoice + paid portion invoice
                if aru.get('paid_amount'):
                    upsert_invoice(
                        partner, f'IC|ARU|PAID|{partner.id}',
                        'UTU OUZ Late Chief Eni Aru (Belgium) — paid portion',
                        product_aru, aru['paid_amount'], True, '2026-01-01',
                    )
                if aru.get('balance'):
                    upsert_invoice(
                        partner, f'IC|ARU|{partner.id}',
                        'UTU OUZ Late Chief Eni Aru (Belgium)',
                        product_aru, aru['balance'], False, '2026-01-01',
                    )
            else:
                upsert_invoice(
                    partner, f'IC|ARU|{partner.id}',
                    'UTU OUZ Late Chief Eni Aru (Belgium)',
                    product_aru, amt, aru['status'] == 'paid', '2026-01-01',
                )
        # Ambulance / Abiriba project levy
        amb = row['ambulance']
        if amb['status'] != 'none':
            if amb['status'] == 'partial':
                if amb.get('paid_amount'):
                    upsert_invoice(
                        partner, f'IC|AMB|PAID|{partner.id}',
                        'Project Levy (Abiriba Ambulance) — paid portion',
                        product_amb, amb['paid_amount'], True, '2026-01-01',
                    )
                if amb.get('balance'):
                    upsert_invoice(
                        partner, f'IC|AMB|{partner.id}',
                        'Project Levy (Abiriba Ambulance)',
                        product_amb, amb['balance'], False, '2026-01-01',
                    )
            else:
                amt = amb.get('paid_amount') or amb.get('balance') or 0.0
                upsert_invoice(
                    partner, f'IC|AMB|{partner.id}',
                    'Project Levy (Abiriba Ambulance)',
                    product_amb, amt, amb['status'] == 'paid', '2026-01-01',
                )

env.cr.commit()

ic_moves = Move.search([('ref', 'ilike', 'IC|%'), ('company_id', '=', central.id), ('state', '!=', 'cancel')])
print('=== IC PAYMENT IMPORT DONE ===')
print(f'created={created} marked_paid_ops={paid_n} unpaid_touched={unpaid_n} skipped={skipped}')
print(f'missing_partner={missing_partner} cancelled_drafts={cancelled_drafts}')
print(f'IC invoices total={len(ic_moves)}')
print('by payment_state:', dict(
    (s, Move.search_count([('id', 'in', ic_moves.ids), ('payment_state', '=', s)]))
    for s in ('paid', 'not_paid', 'partial', 'in_payment')
))
print('amount paid', sum(ic_moves.filtered(lambda m: m.payment_state == 'paid').mapped('amount_total')))
print('amount open', sum(ic_moves.filtered(lambda m: m.payment_state == 'not_paid').mapped('amount_residual')))
if errors[:15]:
    print('sample issues:')
    for e in errors[:15]:
        print(' ', e)
