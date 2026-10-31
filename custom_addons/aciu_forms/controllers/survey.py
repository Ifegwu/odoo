# Part of ACIU Odoo customization.

from odoo.http import request
from odoo.addons.survey.controllers.main import Survey


class AciuSurvey(Survey):
    def survey_start(self, survey_token, answer_token=None, email=False, **post):
        """Public fill page. A closed form explains itself instead of sending people to login."""
        survey = request.env['survey.survey'].sudo().search([
            ('access_token', '=', survey_token),
        ], limit=1)
        if survey and survey._aciu_is_closed():
            cookie_token = request.cookies.get('survey_%s' % survey_token)
            if not answer_token and not cookie_token:
                return request.render('aciu_forms.survey_closed_page', {'survey': survey})
        return super().survey_start(
            survey_token, answer_token=answer_token, email=email, **post,
        )
