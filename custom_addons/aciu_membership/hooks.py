# Part of ACIU Odoo customization.


def post_init_hook(env):
    """Nest existing members under their branch contacts (install)."""
    env['res.partner'].search([
        ('is_aciu_member', '=', True),
        ('is_company', '=', False),
    ])._aciu_sync_parent_from_branch()
