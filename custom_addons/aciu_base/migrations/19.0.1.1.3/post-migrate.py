# Part of ACIU Odoo customization.


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.users'].search([])._aciu_apply_central_executive_override()
