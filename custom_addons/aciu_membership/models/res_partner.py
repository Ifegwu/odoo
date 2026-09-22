# Part of ACIU Odoo customization.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
        help='Member home branch / company. Dues are posted on this company.',
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
