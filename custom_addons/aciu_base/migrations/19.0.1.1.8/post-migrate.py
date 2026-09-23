# Part of ACIU Odoo customization.


def migrate(cr, version):
    # Remove broken QWeb inherit if a prior deploy loaded it.
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE key = 'aciu_base.login_layout_aciu'
            OR name = 'ACIU Login Layout'
        """
    )
