# Part of ACIU Odoo customization.

from odoo import fields, models


class AciuLevyCampaign(models.Model):
    _name = 'aciu.levy.campaign'
    _description = 'ACIU Levy / Project Campaign'
    _order = 'date_start desc, id desc'

    name = fields.Char(required=True)
    contribution_type = fields.Selection(
        [
            ('branch_project', 'Branch Project'),
            ('central_project', 'Central Project'),
            ('burial_levy', 'Burial Levy'),
        ],
        required=True,
        default='burial_levy',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('closed', 'Closed'),
        ],
        default='draft',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Collecting Company',
        required=True,
        default=lambda self: self.env.company,
        domain="[('is_aciu_company', '=', True)]",
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('aciu_contribution_type', 'in', ['branch_project', 'central_project', 'burial_levy'])]",
    )
    amount = fields.Monetary(required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    date_start = fields.Date(default=fields.Date.context_today)
    date_end = fields.Date()
    notes = fields.Text(
        help='Burial / project context. Unpaid amounts are soft debt only.',
    )
    soft_debt_policy = fields.Char(
        default='Unpaid amounts do not block membership; tracked until cleared.',
        readonly=True,
    )

    def action_open(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'draft'})
