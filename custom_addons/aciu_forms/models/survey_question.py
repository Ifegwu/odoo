# Part of ACIU Odoo customization.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    aciu_answer_slot = fields.Selection(
        [
            ('name', 'Full name'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('city', 'City'),
            ('comment', 'Comment'),
        ],
        string='Save Answer As',
        help='Used when an officer accepts a join request or a profile confirmation. '
             'A questionnaire does not write these onto a contact.',
    )

    @api.constrains('aciu_answer_slot', 'survey_id', 'is_page')
    def _check_aciu_answer_slot(self):
        for question in self.filtered('aciu_answer_slot'):
            if question.is_page:
                raise ValidationError(_('A section cannot store an answer on a member.'))
            if question.aciu_answer_slot == 'comment':
                continue
            duplicate = self.search([
                ('id', '!=', question.id),
                ('survey_id', '=', question.survey_id.id),
                ('aciu_answer_slot', '=', question.aciu_answer_slot),
            ], limit=1)
            if duplicate:
                labels = dict(self._fields['aciu_answer_slot']._description_selection(self.env))
                raise ValidationError(_(
                    'Only one question on "%(form)s" can be saved as %(slot)s.',
                    form=question.survey_id.title,
                    slot=labels.get(question.aciu_answer_slot, question.aciu_answer_slot),
                ))
