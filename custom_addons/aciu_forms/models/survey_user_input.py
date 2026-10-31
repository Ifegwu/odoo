# Part of ACIU Odoo customization.

from odoo import fields, models


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _mark_done(self):
        res = super()._mark_done()
        self.filtered(lambda answer: not answer.test_entry)._aciu_create_submission()
        return res

    def _aciu_line_text(self, line):
        if line.skipped:
            return ''
        if line.answer_type == 'char_box':
            return line.value_char_box or ''
        if line.answer_type == 'text_box':
            return line.value_text_box or ''
        if line.answer_type == 'numerical_box':
            return '' if line.value_numerical_box is False else str(line.value_numerical_box)
        if line.answer_type == 'scale':
            return '' if not line.value_scale and line.value_scale != 0 else str(line.value_scale)
        if line.answer_type == 'date' and line.value_date:
            return fields.Date.to_string(line.value_date)
        if line.answer_type == 'datetime' and line.value_datetime:
            return fields.Datetime.to_string(line.value_datetime)
        if line.answer_type == 'suggestion':
            choice = line.suggested_answer_id.value or ''
            if line.matrix_row_id:
                return '%s: %s' % (line.matrix_row_id.value or '', choice)
            return choice
        return line.display_name or ''

    def _aciu_answer_summary(self):
        self.ensure_one()
        chunks = []
        questions = self.survey_id.question_ids.sorted('sequence')
        for question in questions:
            lines = self.user_input_line_ids.filtered(
                lambda line, question=question: line.question_id == question and not line.skipped
            )
            values = [text for text in (self._aciu_line_text(line) for line in lines) if text]
            if values:
                title = question.title or ''
                chunks.append('%s: %s' % (title, ', '.join(values)))
        return '\n'.join(chunks)

    def _aciu_slot_values(self):
        """Map slotted questions to plain text. Comment may repeat; other slots keep the first value."""
        self.ensure_one()
        values = {}
        comments = []
        for line in self.user_input_line_ids.filtered(lambda item: not item.skipped):
            slot = line.question_id.aciu_answer_slot
            if not slot:
                continue
            text = (self._aciu_line_text(line) or '').strip()
            if not text:
                continue
            if slot == 'comment':
                comments.append(text)
            elif slot not in values:
                values[slot] = text
        if comments:
            values['comment'] = '\n'.join(comments)
        return values

    def _aciu_create_submission(self):
        Submission = self.env['aciu.form.submission'].sudo()
        for answer in self:
            if Submission.search_count([('user_input_id', '=', answer.id)]):
                continue
            purpose = answer.survey_id.form_purpose or 'questionnaire'
            partner = answer.partner_id
            if purpose == 'intake' and not partner:
                email = (answer._aciu_slot_values().get('email') or answer.email or '').strip()
                if email:
                    matches = self.env['res.partner'].sudo().search([
                        ('email', '=ilike', email),
                        ('is_company', '=', False),
                    ])
                    if len(matches) == 1:
                        partner = matches
            state = 'recorded' if purpose in ('questionnaire', 'interest', 'registration') else 'pending'
            Submission.create({
                'user_input_id': answer.id,
                'partner_id': partner.id if partner else False,
                'state': state,
                'answer_summary': answer._aciu_answer_summary(),
            })
