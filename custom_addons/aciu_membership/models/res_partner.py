# Part of ACIU Odoo customization.

import functools

from odoo import _, api, fields, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _check_access(self, operation: str):
        """Settings Admin bypasses ACIU partner record rules.

        Admin must correct member profiles Germany-wide. Group-specific ACIU
        ir.rules (OR'd) still interact badly with company contacts such as
        ACIU Germany (res.partner of the central company) during form loads.
        """
        if not self.env.su and self.env.user.has_group('base.group_system'):
            Access = self.env['ir.model.access']
            if not Access.check(self._name, operation, raise_exception=False):
                return self, functools.partial(
                    Access._make_access_error, self._name, operation,
                )
            return None
        return super()._check_access(operation)

    is_aciu_member = fields.Boolean(
        string='ACIU Member',
        help='Mark this contact as an ACIU member.',
    )
    aciu_member_id = fields.Char(
        string='ACIU Member ID',
        copy=False,
        index=True,
        help='Unique ACIU identifier (optional NIN/diaspora ID later).',
    )
    aciu_branch_id = fields.Many2one(
        'res.company',
        string='Home Branch',
        domain="[('is_aciu_company', '=', True)]",
        help='Member home branch / company. Dues are posted on this company. '
             'Also nests the contact under that branch in Contacts.',
    )
    aciu_membership_status = fields.Selection(
        [
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('pending', 'Pending'),
            ('deceased', 'Deceased'),
        ],
        string='Membership Status',
        default='active',
    )
    aciu_age_grade = fields.Char(
        string='Age Grade',
        help='Traditional age grade / generation group when applicable.',
    )
    aciu_join_date = fields.Date(string='Join Date')
    aciu_open_debt = fields.Monetary(
        string='Open Debt',
        compute='_compute_aciu_open_debt',
        currency_field='currency_id',
        help='Outstanding ACIU invoices. Soft tracking only — does not block membership.',
    )
    aciu_has_open_debt = fields.Boolean(
        string='Has Open Debt',
        compute='_compute_aciu_open_debt',
    )

    def _aciu_branch_partner(self):
        self.ensure_one()
        return self.aciu_branch_id.partner_id if self.aciu_branch_id else self.env['res.partner']

    def _aciu_sync_parent_from_branch(self):
        """Nest individual members under their branch company contact."""
        for partner in self:
            if partner.is_company or not partner.is_aciu_member:
                continue
            branch_partner = partner._aciu_branch_partner()
            if not branch_partner:
                continue
            # Only rewrite when missing or still pointing at another ACIU company contact
            other_aciu_parents = self.env['res.company'].sudo().search([
                ('is_aciu_company', '=', True),
            ]).mapped('partner_id')
            if partner.parent_id == branch_partner:
                continue
            if partner.parent_id and partner.parent_id not in other_aciu_parents:
                # Respect a manually set non-ACIU employer/parent
                continue
            partner.with_context(aciu_skip_parent_sync=True).write({
                'parent_id': branch_partner.id,
                'type': 'contact',
            })

    @api.onchange('aciu_branch_id', 'is_aciu_member')
    def _onchange_aciu_branch_hierarchy(self):
        for partner in self:
            if partner.is_company or not partner.is_aciu_member:
                continue
            branch_partner = partner._aciu_branch_partner()
            if branch_partner:
                partner.parent_id = branch_partner

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._aciu_sync_parent_from_branch()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('aciu_skip_parent_sync'):
            return res
        if 'aciu_branch_id' in vals or 'is_aciu_member' in vals or 'parent_id' in vals:
            self._aciu_sync_parent_from_branch()
        return res

    @api.model
    def _aciu_active_company_id(self):
        """Current company from the web switcher (first allowed_company_ids)."""
        cids = self.env.context.get('allowed_company_ids') or []
        if cids:
            return cids[0]
        return self.env.company.id

    @api.model
    def _aciu_member_branch_domain(self):
        """Branch members for a leaf company; all descendant members for central."""
        company = self.env['res.company'].browse(self._aciu_active_company_id())
        if company.child_ids:
            return [('aciu_branch_id', 'child_of', company.id)]
        return [('aciu_branch_id', '=', company.id)]

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        if self.env.context.get('aciu_filter_current_branch'):
            domain = expression.AND([
                list(domain or []),
                self._aciu_member_branch_domain(),
            ])
        return super()._search(
            domain, offset=offset, limit=limit, order=order,
            active_test=active_test, bypass_access=bypass_access,
        )

    @api.model
    def action_aciu_open_members(self):
        """Open ACIU members for the switcher company (branch or whole Germany)."""
        company_id = self._aciu_active_company_id()
        company = self.env['res.company'].browse(company_id)
        ctx = {
            'default_is_aciu_member': True,
            'default_aciu_membership_status': 'active',
            'default_aciu_branch_id': company_id,
            'aciu_filter_current_branch': True,
        }
        if company.child_ids:
            ctx['group_by'] = 'aciu_branch_id'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members'),
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('aciu_membership.view_partner_tree_aciu_members').id, 'list'),
                (False, 'form'),
            ],
            'domain': expression.AND([
                [('is_aciu_member', '=', True)],
                self._aciu_member_branch_domain(),
            ]),
            'context': ctx,
        }

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.payment_state', 'invoice_ids.state', 'is_aciu_member')
    def _compute_aciu_open_debt(self):
        Move = self.env['account.move']
        for partner in self:
            if not partner.is_aciu_member:
                partner.aciu_open_debt = 0.0
                partner.aciu_has_open_debt = False
                continue
            invoices = Move.search([
                ('partner_id', 'child_of', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial', 'in_payment')),
            ])
            residual = sum(invoices.mapped('amount_residual'))
            partner.aciu_open_debt = residual
            partner.aciu_has_open_debt = bool(residual)
