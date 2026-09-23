# Part of ACIU Odoo customization.

from odoo import api, models
from odoo.fields import Command

# Branch titles superseded when the user is Central Executive.
_ACIU_BRANCH_OFFICER_XMLIDS = (
    'aciu_base.group_aciu_branch_treasurer',
    'aciu_base.group_aciu_branch_financial_secretary',
    'aciu_base.group_aciu_branch_secretary',
    'aciu_base.group_aciu_branch_speaker',
    'aciu_base.group_aciu_branch_vice_president',
    'aciu_base.group_aciu_branch_leader',
)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _aciu_branch_officer_groups(self):
        groups = self.env['res.groups']
        for xmlid in _ACIU_BRANCH_OFFICER_XMLIDS:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _aciu_apply_central_executive_override(self):
        """Central Executive overrides any branch officer title.

        The user remains a branch member via company_ids / home branch; branch
        officer groups are removed so Germany-wide central rights apply alone.
        """
        if self.env.context.get('aciu_skip_central_override'):
            return
        central = self.env.ref(
            'aciu_base.group_aciu_central_executive', raise_if_not_found=False,
        )
        if not central:
            return
        officers = self._aciu_branch_officer_groups()
        if not officers:
            return
        for user in self:
            if central not in user.all_group_ids:
                continue
            to_remove = user.group_ids & officers
            if to_remove:
                user.with_context(aciu_skip_central_override=True).write({
                    'group_ids': [Command.unlink(g.id) for g in to_remove],
                })

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._aciu_apply_central_executive_override()
        return users

    def write(self, vals):
        res = super().write(vals)
        self._aciu_apply_central_executive_override()
        return res
