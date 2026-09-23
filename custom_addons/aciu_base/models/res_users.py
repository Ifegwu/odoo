# Part of ACIU Odoo customization.

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _aciu_has_central_executive(self):
        """True if the user has Central Executive (implies Germany-wide ops)."""
        self.ensure_one()
        central = self.env.ref(
            'aciu_base.group_aciu_central_executive', raise_if_not_found=False,
        )
        return bool(central and central in self.all_group_ids)
