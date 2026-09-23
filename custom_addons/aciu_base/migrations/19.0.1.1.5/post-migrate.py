# Part of ACIU Odoo customization.


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        'aciu_base.res_company_rule_aciu_read_parents',
        raise_if_not_found=False,
    )
    if rule:
        rule.unlink()
