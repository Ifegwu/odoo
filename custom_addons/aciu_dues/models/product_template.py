# Part of ACIU Odoo customization.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    aciu_contribution_type = fields.Selection(
        [
            ('annual_due', 'Annual Membership Due'),
            ('roll_call_fee', 'Monthly Roll-Call Fee'),
            ('branch_project', 'Branch Project Contribution'),
            ('central_project', 'Central Project Contribution'),
            ('burial_levy', 'Burial Levy'),
            ('event_fee', 'Event Fee'),
        ],
        string='ACIU Contribution Type',
        help='Classifies products used for ACIU collections.',
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    aciu_contribution_type = fields.Selection(
        related='product_tmpl_id.aciu_contribution_type',
        store=True,
        readonly=False,
    )
