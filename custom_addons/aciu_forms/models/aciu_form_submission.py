# Part of ACIU Odoo customization.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PARTNER_SLOTS = {
    'name': 'name',
    'email': 'email',
    'phone': 'phone',
    'city': 'city',
}


class AciuFormSubmission(models.Model):
    _name = 'aciu.form.submission'
    _description = 'ACIU Form Response'
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name', store=True)
    survey_id = fields.Many2one(
        'survey.survey',
        required=True,
        readonly=True,
        ondelete='cascade',
        index=True,
    )
    user_input_id = fields.Many2one(
        'survey.user_input',
        string='Answer',
        required=True,
        readonly=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='survey_id.aciu_company_id',
        store=True,
        index=True,
        readonly=True,
    )
    form_purpose = fields.Selection(
        related='survey_id.form_purpose',
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True)
    email = fields.Char(related='user_input_id.email', readonly=True)
    answer_summary = fields.Text(string='Answers', readonly=True)
    state = fields.Selection(
        [
            ('recorded', 'Recorded'),
            ('pending', 'To Review'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        required=True,
        default='pending',
        index=True,
        readonly=True,
    )
    attendance_marked = fields.Boolean(
        string='Marked Present',
        readonly=True,
        help='Set when an officer accepts a roll-call check-in. '
             'The roll-call fee is not invoiced from this form.',
    )
    applied_partner_id = fields.Many2one(
        'res.partner',
        string='Applied On',
        readonly=True,
    )
    reviewed_by_id = fields.Many2one('res.users', string='Reviewed By', readonly=True)
    reviewed_on = fields.Datetime(string='Reviewed On', readonly=True)

    _user_input_unique = models.Constraint(
        'unique(user_input_id)',
        'Each submitted answer can only be recorded once.',
    )

    @api.depends('survey_id.title', 'partner_id.name', 'user_input_id.email', 'user_input_id.nickname')
    def _compute_name(self):
        for submission in self:
            answer = submission.user_input_id
            who = (
                submission.partner_id.name
                or (answer.email if answer else False)
                or (answer.nickname if answer else False)
                or _('Anonymous')
            )
            title = submission.survey_id.title or _('Form')
            submission.name = '%s — %s' % (title, who)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('user_input_id') and not vals.get('survey_id'):
                answer = self.env['survey.user_input'].browse(vals['user_input_id'])
                vals['survey_id'] = answer.survey_id.id
        return super().create(vals_list)

    def action_accept(self):
        for submission in self:
            if submission.state != 'pending':
                raise UserError(_('Only responses waiting for review can be accepted.'))
            handler = {
                'intake': submission._aciu_accept_intake,
                'profile': submission._aciu_accept_profile,
                'attendance': submission._aciu_accept_attendance,
            }.get(submission.form_purpose, submission._aciu_mark_reviewed)
            handler()
        return True

    def action_reject(self):
        for submission in self:
            if submission.state != 'pending':
                raise UserError(_('Only responses waiting for review can be rejected.'))
            submission.write({
                'state': 'rejected',
                'reviewed_by_id': self.env.user.id,
                'reviewed_on': fields.Datetime.now(),
            })
        return True

    def _aciu_review_vals(self, extra=None):
        vals = {
            'state': 'accepted',
            'reviewed_by_id': self.env.user.id,
            'reviewed_on': fields.Datetime.now(),
        }
        if extra:
            vals.update(extra)
        return vals

    def _aciu_mark_reviewed(self):
        self.ensure_one()
        self.write(self._aciu_review_vals())

    def _aciu_partner_vals_from_slots(self, slots, only_filled=True):
        vals = {}
        for slot, field_name in PARTNER_SLOTS.items():
            value = (slots.get(slot) or '').strip()
            if value or not only_filled:
                if value:
                    vals[field_name] = value
        return vals

    def _aciu_accept_intake(self):
        """Create or flag a pending member. Does not run from the public link itself."""
        self.ensure_one()
        slots = self.user_input_id._aciu_slot_values()
        partner = self.partner_id
        if partner and partner.is_company:
            partner = self.env['res.partner']
        if partner:
            vals = {}
            if not partner.is_aciu_member:
                vals['is_aciu_member'] = True
            if not partner.aciu_branch_id:
                vals['aciu_branch_id'] = self.company_id.id
            if partner.aciu_membership_status != 'active':
                vals['aciu_membership_status'] = 'pending'
            if not partner.aciu_join_date:
                vals['aciu_join_date'] = fields.Date.context_today(self)
            filled = self._aciu_partner_vals_from_slots(slots)
            filled.pop('name', None)
            for field_name, value in filled.items():
                if not partner[field_name]:
                    vals[field_name] = value
            if vals:
                partner.sudo().write(vals)
        else:
            name = (slots.get('name') or '').strip()
            if not name:
                raise UserError(_(
                    'Add a question saved as Full name before accepting this join request.'
                ))
            partner = self.env['res.partner'].sudo().create({
                'name': name,
                'email': slots.get('email') or False,
                'phone': slots.get('phone') or False,
                'city': slots.get('city') or False,
                'company_id': self.company_id.id,
                'is_aciu_member': True,
                'aciu_branch_id': self.company_id.id,
                'aciu_membership_status': 'pending',
                'aciu_join_date': fields.Date.context_today(self),
            })
        self.write(self._aciu_review_vals({
            'partner_id': partner.id,
            'applied_partner_id': partner.id,
        }))

    def _aciu_accept_profile(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_(
                'Profile forms must be sent with Share as a personal invite, '
                'so the answer is tied to a member. An open link cannot change a contact.'
            ))
        if partner.is_company:
            raise UserError(_('A company contact cannot be updated from a profile form.'))
        if partner.aciu_branch_id and partner.aciu_branch_id != self.company_id:
            if not self.env.user.has_group('aciu_base.group_aciu_central_executive'):
                raise UserError(_('This member belongs to another branch.'))
        vals = self._aciu_partner_vals_from_slots(self.user_input_id._aciu_slot_values())
        if vals:
            partner.sudo().write(vals)
        if not partner.aciu_branch_id:
            partner.sudo().write({'aciu_branch_id': self.company_id.id})
        self.write(self._aciu_review_vals({
            'applied_partner_id': partner.id,
        }))

    def _aciu_accept_attendance(self):
        """Record presence only. The treasurer still posts the roll-call fee."""
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            raise UserError(_(
                'Roll-call check-in must be a personal invite sent to the member. '
                'An open link cannot mark someone present.'
            ))
        if partner.aciu_branch_id != self.company_id:
            raise UserError(_('This member is not in the branch that owns the form.'))
        self.write(self._aciu_review_vals({
            'attendance_marked': True,
            'applied_partner_id': partner.id,
        }))
