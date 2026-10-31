# Part of ACIU Odoo customization.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.urls import urljoin as url_join

# Stock Surveys lets every survey user read a form whose "Restricted to" list
# is empty. ACIU forms are limited to the branch company as well, so Berlin
# does not read Hamburg. Survey managers (central executive, Settings admin)
# keep their own rule and still see every form.
ACIU_SURVEY_USER_RULES = {
    'survey.survey_survey_rule_survey_user': (
        "['&', "
        "'|', ('restrict_user_ids', 'in', user.id), ('restrict_user_ids', '=', False), "
        "('aciu_company_id', 'in', company_ids)]"
    ),
    'survey.survey_question_rule_survey_user': (
        "['&', "
        "'|', ('survey_id.restrict_user_ids', 'in', user.id), "
        "('survey_id.restrict_user_ids', '=', False), "
        "('survey_id.aciu_company_id', 'in', company_ids)]"
    ),
    'survey.survey_question_answer_rule_survey_user': (
        "['&', "
        "'|', "
        "'|', ('question_id.survey_id.restrict_user_ids', 'in', user.id), "
        "('matrix_question_id.survey_id.restrict_user_ids', 'in', user.id), "
        "'|', ('question_id.survey_id.restrict_user_ids', '=', False), "
        "('matrix_question_id.survey_id.restrict_user_ids', '=', False), "
        "'|', ('question_id.survey_id.aciu_company_id', 'in', company_ids), "
        "('matrix_question_id.survey_id.aciu_company_id', 'in', company_ids)]"
    ),
    'survey.survey_user_input_rule_survey_user': (
        "['&', '&', "
        "('survey_id.survey_type', 'in', "
        "('assessment', 'custom', 'live_session', 'survey')), "
        "'|', ('survey_id.restrict_user_ids', 'in', user.id), "
        "('survey_id.restrict_user_ids', '=', False), "
        "('survey_id.aciu_company_id', 'in', company_ids)]"
    ),
    'survey.survey_user_input_line_rule_survey_user': (
        "['&', '&', "
        "('survey_id.survey_type', 'in', "
        "('assessment', 'custom', 'live_session', 'survey')), "
        "'|', ('survey_id.restrict_user_ids', 'in', user.id), "
        "('survey_id.restrict_user_ids', '=', False), "
        "('survey_id.aciu_company_id', 'in', company_ids)]"
    ),
    'survey.survey_invite_survey_user': (
        "['&', "
        "'|', ('survey_id.restrict_user_ids', 'in', user.id), "
        "('survey_id.restrict_user_ids', '=', False), "
        "('survey_id.aciu_company_id', 'in', company_ids)]"
    ),
}


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    aciu_company_id = fields.Many2one(
        'res.company',
        string='Branch',
        required=True,
        index=True,
        default=lambda self: self._default_aciu_company_id(),
        domain="[('is_aciu_company', '=', True)]",
        help='Branch that owns this form. Officers of other branches cannot read it.',
    )
    form_purpose = fields.Selection(
        [
            ('questionnaire', 'Questionnaire'),
            ('intake', 'Join / intake'),
            ('profile', 'Profile confirmation'),
            ('attendance', 'Roll-call check-in'),
            ('interest', 'Project interest'),
            ('registration', 'Event registration'),
        ],
        string='Purpose',
        required=True,
        default='questionnaire',
        help='Questionnaire, interest, and registration are stored as-is. '
             'Join, profile, and roll-call wait for an officer before anything '
             'is written on a member.',
    )
    closes_on = fields.Datetime(
        string='Closes On',
        help='After this moment new respondents cannot start. '
             'Someone who already started can still finish.',
    )
    aciu_public_url = fields.Char(
        string='Public Link',
        compute='_compute_aciu_public_url',
        help='Share this link. The respondent does not log in and does not open the portal.',
    )
    aciu_submission_count = fields.Integer(compute='_compute_aciu_submission_count')

    @api.model
    def _default_aciu_company_id(self):
        company = self.env.company
        if company.is_aciu_company:
            return company
        return self.env['res.company'].search([('is_aciu_company', '=', True)], limit=1)

    @api.depends('access_token')
    def _compute_aciu_public_url(self):
        for survey in self:
            if survey.access_token:
                survey.aciu_public_url = url_join(
                    survey.get_base_url(), survey.get_start_url(),
                )
            else:
                survey.aciu_public_url = False

    def _compute_aciu_submission_count(self):
        Submission = self.env['aciu.form.submission']
        for survey in self:
            survey.aciu_submission_count = Submission.search_count([
                ('survey_id', '=', survey.id),
            ])

    def _aciu_is_closed(self):
        self.ensure_one()
        if not self.active:
            return True
        return bool(self.closes_on and fields.Datetime.now() > self.closes_on)

    def _check_answer_creation(self, user, partner, email, test_entry=False,
                               check_attempts=True, invite_token=False):
        self.ensure_one()
        if not test_entry and self._aciu_is_closed():
            raise UserError(_('This form is closed.'))
        return super()._check_answer_creation(
            user, partner, email,
            test_entry=test_entry,
            check_attempts=check_attempts,
            invite_token=invite_token,
        )

    def action_aciu_open_submissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Responses'),
            'res_model': 'aciu.form.submission',
            'view_mode': 'list,form',
            'domain': [('survey_id', '=', self.id)],
        }

    @api.model
    def _aciu_apply_survey_user_rules(self):
        """Limit stock survey-user rules to the form's branch company."""
        for xmlid, domain in ACIU_SURVEY_USER_RULES.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if rule:
                rule.sudo().write({'domain_force': domain})
