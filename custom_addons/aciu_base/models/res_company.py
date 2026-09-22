# Part of ACIU Odoo customization.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_aciu_company = fields.Boolean(
        string='ACIU Company',
        help='Mark companies that belong to the ACIU organization tree.',
    )
    is_registered_ev = fields.Boolean(
        string='Registered e.V.',
        help='True for legally registered Vereine (e.g. ACIU Germany central). '
             'Branches flip this when they register — no company restructuring needed.',
    )
    aciu_branch_code = fields.Char(
        string='ACIU Branch Code',
        help='Stable code such as DE-BE for Berlin-Brandenburg.',
        index=True,
    )
    roll_call_fee_amount = fields.Monetary(
        string='Monthly Roll-Call Fee',
        currency_field='currency_id',
        help='Per-branch monthly roll-call fee. Berlin-Brandenburg = 5 EUR; others TBD.',
    )
    aciu_vr_number = fields.Char(
        string='VR Number',
        help='Vereinsregister number when registered as e.V.',
    )
