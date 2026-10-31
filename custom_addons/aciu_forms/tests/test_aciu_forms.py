# Part of ACIU Odoo customization.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAciuForms(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['survey.survey']._aciu_apply_survey_user_rules()
        cls.berlin = cls.env.ref('aciu_base.company_aciu_berlin')
        cls.hamburg = cls.env.ref('aciu_base.company_aciu_hamburg')
        cls.secretary = cls.env['res.users'].create({
            'name': 'Berlin Secretary',
            'login': 'aciu_forms_berlin_secretary',
            'email': 'aciu_forms_berlin_secretary@example.com',
            'company_id': cls.berlin.id,
            'company_ids': [(6, 0, [cls.berlin.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('survey.group_survey_user').id,
                cls.env.ref('aciu_base.group_aciu_branch_secretary').id,
            ])],
        })

    def _form(self, company, purpose, title='ACIU form'):
        survey = self.env['survey.survey'].create({
            'title': title,
            'aciu_company_id': company.id,
            'form_purpose': purpose,
            'access_mode': 'public',
            'users_login_required': False,
            'questions_layout': 'one_page',
        })
        name_q = self.env['survey.question'].create({
            'survey_id': survey.id,
            'title': 'Full name',
            'question_type': 'char_box',
            'aciu_answer_slot': 'name',
        })
        email_q = self.env['survey.question'].create({
            'survey_id': survey.id,
            'title': 'Email',
            'question_type': 'char_box',
            'aciu_answer_slot': 'email',
        })
        return survey, name_q, email_q

    def _submit(self, survey, name_q, email_q, name, email, partner=None):
        answer = survey._create_answer(partner=partner, email=email)
        answer._save_lines(name_q, name)
        answer._save_lines(email_q, email)
        answer._mark_done()
        submission = self.env['aciu.form.submission'].search([
            ('user_input_id', '=', answer.id),
        ])
        return answer, submission

    def test_public_link_and_questionnaire_does_not_touch_contacts(self):
        survey, name_q, email_q = self._form(self.berlin, 'questionnaire', 'Branch questionnaire')
        self.assertIn('/survey/start/', survey.aciu_public_url)
        self.assertFalse(survey.users_login_required)
        before = self.env['res.partner'].search_count([])
        answer, submission = self._submit(
            survey, name_q, email_q, 'Ada Okoro', 'ada.forms@example.com',
        )
        self.assertEqual(answer.state, 'done')
        self.assertEqual(submission.state, 'recorded')
        self.assertFalse(submission.partner_id)
        self.assertIn('Ada Okoro', submission.answer_summary)
        self.assertEqual(self.env['res.partner'].search_count([]), before)

    def test_intake_waits_for_officer_then_creates_pending_member(self):
        survey, name_q, email_q = self._form(self.berlin, 'intake', 'Join Berlin')
        _answer, submission = self._submit(
            survey, name_q, email_q, 'Chidi Nwosu', 'chidi.forms@example.com',
        )
        self.assertEqual(submission.state, 'pending')
        self.assertFalse(self.env['res.partner'].search([
            ('email', '=', 'chidi.forms@example.com'),
        ]))
        submission.with_user(self.secretary).action_accept()
        partner = self.env['res.partner'].search([
            ('email', '=', 'chidi.forms@example.com'),
        ])
        self.assertEqual(len(partner), 1)
        self.assertTrue(partner.is_aciu_member)
        self.assertEqual(partner.aciu_branch_id, self.berlin)
        self.assertEqual(partner.aciu_membership_status, 'pending')
        self.assertEqual(submission.state, 'accepted')
        self.assertEqual(submission.applied_partner_id, partner)

    def test_profile_and_attendance_require_a_bound_member(self):
        profile, name_q, email_q = self._form(self.berlin, 'profile', 'Confirm profile')
        _answer, submission = self._submit(
            profile, name_q, email_q, 'Nobody', 'nobody.forms@example.com',
        )
        with self.assertRaises(UserError):
            submission.action_accept()

        member = self.env['res.partner'].create({
            'name': 'Berlin Member',
            'email': 'member.forms@example.com',
            'is_aciu_member': True,
            'aciu_branch_id': self.berlin.id,
            'aciu_membership_status': 'active',
        })
        phone_q = self.env['survey.question'].create({
            'survey_id': profile.id,
            'title': 'Phone',
            'question_type': 'char_box',
            'aciu_answer_slot': 'phone',
        })
        answer = profile._create_answer(partner=member, email=member.email)
        answer._save_lines(phone_q, '+491511234567')
        answer._mark_done()
        bound = self.env['aciu.form.submission'].search([
            ('user_input_id', '=', answer.id),
        ])
        bound.action_accept()
        self.assertEqual(member.phone, '+491511234567')
        self.assertEqual(member.aciu_membership_status, 'active')

        other = self.env['res.partner'].create({
            'name': 'Hamburg Member',
            'email': 'hh.forms@example.com',
            'is_aciu_member': True,
            'aciu_branch_id': self.hamburg.id,
        })
        roll, roll_name, roll_email = self._form(self.berlin, 'attendance', 'Berlin roll call')
        _answer, wrong = self._submit(
            roll, roll_name, roll_email, other.name, other.email, partner=other,
        )
        with self.assertRaises(UserError):
            wrong.action_accept()
        self.assertFalse(wrong.attendance_marked)

        _answer, present = self._submit(
            roll, roll_name, roll_email, member.name, member.email, partner=member,
        )
        invoices_before = self.env['account.move'].search_count([])
        present.action_accept()
        self.assertTrue(present.attendance_marked)
        self.assertEqual(present.state, 'accepted')
        self.assertEqual(self.env['account.move'].search_count([]), invoices_before)

    def test_closed_form_rejects_new_answers(self):
        survey, _name_q, _email_q = self._form(self.berlin, 'questionnaire', 'Closed form')
        survey.closes_on = fields.Datetime.now() - timedelta(hours=1)
        with self.assertRaises(UserError):
            survey._create_answer(email='late@example.com')

    def test_branch_secretary_cannot_read_another_branch_form(self):
        berlin_form, _n, _e = self._form(self.berlin, 'questionnaire', 'Berlin only')
        hamburg_form, _n, _e = self._form(self.hamburg, 'questionnaire', 'Hamburg only')
        visible = self.env['survey.survey'].with_user(self.secretary).search([
            ('id', 'in', (berlin_form.id, hamburg_form.id)),
        ])
        self.assertEqual(visible, berlin_form)
        hamburg_answer = hamburg_form._create_answer(email='hh-guest@example.com')
        hamburg_answer._mark_done()
        leaked = self.env['aciu.form.submission'].with_user(self.secretary).search([
            ('survey_id', '=', hamburg_form.id),
        ])
        self.assertFalse(leaked)

    def test_one_slot_per_form(self):
        survey, _name_q, _email_q = self._form(self.berlin, 'intake', 'Slots')
        with self.assertRaises(ValidationError):
            self.env['survey.question'].create({
                'survey_id': survey.id,
                'title': 'Name again',
                'question_type': 'char_box',
                'aciu_answer_slot': 'name',
            })
