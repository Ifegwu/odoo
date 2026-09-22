# Part of ACIU Odoo customization.


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.partner'].search([
        ('is_aciu_member', '=', True),
        ('is_company', '=', False),
    ])._aciu_sync_parent_from_branch()
