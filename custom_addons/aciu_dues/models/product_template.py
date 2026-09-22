# Part of ACIU Odoo customization.

from odoo import api, fields, models


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
        help='Classifies products used for ACIU collections. These products are always tax-free.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('aciu_contribution_type'):
                vals['taxes_id'] = [(5,)]
                vals['supplier_taxes_id'] = [(5,)]
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_aciu_tax_clear'):
            return res
        aciu = self.filtered('aciu_contribution_type')
        dirty = aciu.filtered(lambda p: p.taxes_id or p.supplier_taxes_id)
        if dirty:
            dirty.with_context(skip_aciu_tax_clear=True).write({
                'taxes_id': [(5,)],
                'supplier_taxes_id': [(5,)],
            })
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    aciu_contribution_type = fields.Selection(
        related='product_tmpl_id.aciu_contribution_type',
        store=True,
        readonly=False,
    )
