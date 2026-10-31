# Part of ACIU Odoo customization.
{
    'name': 'ACIU Forms',
    'version': '19.0.1.0.0',
    'category': 'ACIU',
    'summary': 'Shareable questionnaires and forms, filled by link without the portal',
    'description': """
ACIU Forms
==========
* Officers build questionnaires and other forms with Surveys
* Anyone with the link fills them on a public page (no /web and no /my portal)
* Personal invites bind an answer to a known member without asking them to log in
* Completed answers become submissions. Intake, profile, and roll-call wait for an officer
* Branch officers see only their branch. An open link never edits a member by itself
    """,
    'author': 'ACIU',
    'license': 'LGPL-3',
    'depends': ['aciu_membership', 'survey'],
    'data': [
        'security/ir.model.access.csv',
        'security/aciu_forms_security.xml',
        'data/aciu_forms_rules.xml',
        'views/survey_views.xml',
        'views/aciu_form_submission_views.xml',
        'views/aciu_forms_menus.xml',
        'views/survey_templates.xml',
    ],
    'assets': {
        'survey.survey_assets': [
            'aciu_forms/static/src/scss/aciu_survey.css',
        ],
    },
    'installable': True,
}
