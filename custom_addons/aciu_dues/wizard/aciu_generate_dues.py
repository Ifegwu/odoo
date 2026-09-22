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
        required=True,
        default='annual_due',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Branch / Company',
        required=True,
        default=lambda self: self.env.company,
        domain="[('is_aciu_company', '=', True)]",
    )
    member_ids = fields.Many2many(
        'res.partner',
        string='Members',
        domain="[('is_aciu_member', '=', True), ('aciu_branch_id', '=', company_id)]",
    )
    invoice_date = fields.Date(required=True, default=fields.Date.context_today)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.member_ids = self.env['res.partner'].search([
                ('is_aciu_member', '=', True),
                ('aciu_branch_id', '=', self.company_id.id),
                ('aciu_membership_status', '=', 'active'),
            ])

    def action_generate(self):
        self.ensure_one()
        if not self.member_ids:
            raise UserError(_('Select at least one member.'))

        if self.dues_type == 'annual_due':
            product = self.env.ref('aciu_dues.product_aciu_annual_due', raise_if_not_found=False)
            amount = 20.0
        else:
            product = self.env.ref('aciu_dues.product_aciu_roll_call_fee', raise_if_not_found=False)
            amount = self.company_id.roll_call_fee_amount
            if not amount:
                raise UserError(_(
                    'Roll-call fee is not set for %(branch)s. '
                    'Set it on the company (Berlin-Brandenburg = 5 EUR).',
                    branch=self.company_id.name,
                ))

        if not product:
            raise UserError(_('ACIU dues products are missing. Update the aciu_dues module.'))

        Move = self.env['account.move'].with_company(self.company_id)
        created = self.env['account.move']
        for member in self.member_ids:
            move = Move.create({
                'move_type': 'out_invoice',
                'partner_id': member.id,
                'company_id': self.company_id.id,
                'invoice_date': self.invoice_date,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': product.display_name,
                    'quantity': 1,
                    'price_unit': amount,
                })],
            })
            created |= move

        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Dues Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'context': {'create': False},
        }
