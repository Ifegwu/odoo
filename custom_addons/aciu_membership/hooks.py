# Part of ACIU Odoo customization.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Nest existing members under their branch contacts (install)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.partner'].search([
        ('is_aciu_member', '=', True),
        ('is_company', '=', False),
    ])._aciu_sync_parent_from_branch()
