# Part of ACIU Odoo customization.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AciuGenerateDuesWizard(models.TransientModel):
    _name = 'aciu.generate.dues.wizard'
    _description = 'Generate ACIU Dues Invoices'

    dues_type = fields.Selection(
        [
            ('annual_due', 'Annual Membership Due (€20)'),
            ('roll_call_fee', 'Monthly Roll-Call Fee'),
        ],
        string='Contribution Type',
        required=True,
        default='annual_due',
        help='Annual dues and roll-call fees are generated here. '
             'Burial levies and projects use ACIU → Projects & Burial Levies.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Branch / Company',
        required=True,
        default=lambda self: self.env.company,
        domain="[('is_aciu_company', '=', True)]",
        help='Only members whose Home Branch is exactly this company. '
             'Select ACIU Berlin-Brandenburg for Berlin members (not Central). '
             'Each invoice is posted on the member\'s Home Branch.',
    )
    member_ids = fields.Many2many(
        'res.partner',
        string='Members',
        domain="[('is_aciu_member', '=', True), ('aciu_membership_status', '=', 'active'), ('aciu_branch_id', '=', company_id)]",
    )
    invoice_date = fields.Date(required=True, default=fields.Date.context_today)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        # Always replace selection so switching Bayern does not keep Berlin tags
        self.member_ids = False
        if self.company_id:
            self.member_ids = self.env['res.partner'].search([
                ('is_aciu_member', '=', True),
                ('aciu_membership_status', '=', 'active'),
                ('aciu_branch_id', '=', self.company_id.id),
            ])

    def _prepare_tax_free_line_vals(self, product, amount):
        """ACIU contributions are never taxed (dues, roll call, etc.)."""
        return {
            'product_id': product.id,
            'name': product.display_name,
            'quantity': 1,
            'price_unit': amount,
            'tax_ids': [(5,)],
        }

    def action_generate(self):
        self.ensure_one()
        if not self.member_ids:
            raise UserError(_(
                'No members selected. Set Branch / Company to the members\' Home Branch '
                '(e.g. ACIU Berlin-Brandenburg), or type a member name in Members.'
            ))

        if self.dues_type == 'annual_due':
            product = self.env.ref('aciu_dues.product_aciu_annual_due', raise_if_not_found=False)
        else:
            product = self.env.ref('aciu_dues.product_aciu_roll_call_fee', raise_if_not_found=False)

        if not product:
            raise UserError(_('ACIU dues products are missing. Update the aciu_dues module.'))

        # Chart load / company defaults may have put VAT on products — strip it.
        if product.taxes_id or product.supplier_taxes_id:
            product.product_tmpl_id.write({
                'taxes_id': [(5,)],
                'supplier_taxes_id': [(5,)],
            })

        created = self.env['account.move']
        for member in self.member_ids:
            branch = member.aciu_branch_id
            if not branch:
                raise UserError(_(
                    '%(member)s has no Home Branch. Set it on the ACIU Membership tab.',
                    member=member.display_name,
                ))

            if self.dues_type == 'annual_due':
                amount = 20.0
            else:
                amount = branch.roll_call_fee_amount
                if not amount:
                    raise UserError(_(
                        'Roll-call fee is not set for %(branch)s. '
                        'Set it on the company (Berlin-Brandenburg = 5 EUR).',
                        branch=branch.display_name,
                    ))

            Move = self.env['account.move'].with_company(branch).with_context(
                skip_computed_taxes=True,
            )
            move = Move.create({
                'move_type': 'out_invoice',
                'partner_id': member.id,
                'company_id': branch.id,
                'invoice_date': self.invoice_date,
                'invoice_line_ids': [(0, 0, self._prepare_tax_free_line_vals(product, amount))],
            })
            # Belt-and-suspenders: income account defaults must not re-add VAT
            move.invoice_line_ids.with_context(skip_computed_taxes=True).write({'tax_ids': [(5,)]})
            move.action_post()
            created |= move

        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Dues Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'context': {'create': False},
        }
