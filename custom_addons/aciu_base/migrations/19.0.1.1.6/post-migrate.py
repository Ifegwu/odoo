# Part of ACIU Odoo customization.


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    from odoo.addons.aciu_base.hooks import apply_aciu_branding

    env = api.Environment(cr, SUPERUSER_ID, {})
    apply_aciu_branding(env)
