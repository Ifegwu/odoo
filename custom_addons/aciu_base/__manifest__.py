# Part of ACIU Odoo customization.
{
    'name': 'ACIU Base',
    'version': '19.0.1.1.7',
    'category': 'ACIU',
    'summary': 'ACIU organization: Germany central + branches, security groups',
    'description': """
ACIU Base
=========
* Multi-company skeleton: ACIU Germany (central e.V.) + 11 DE branches
* is_registered_ev and branch codes on companies
* Per-branch monthly roll-call fee amount (Berlin-Brandenburg = 5 EUR)
* Branch officers: Treasurer, Financial Secretary, Secretary, Speaker, VP, President
* Central Executive keeps branch titles and performs both central and branch functions
* Branding: ACIU logo, aciuworldwide.com colors, login background (bg-login.jpeg)
    """,
    'author': 'ACIU',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/aciu_security.xml',
        'security/ir.model.access.csv',
        'data/aciu_company_data.xml',
        'views/res_company_views.xml',
        'views/aciu_menus.xml',
        'views/login_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            (
                'after',
                'web/static/src/scss/primary_variables.scss',
                'aciu_base/static/src/scss/primary_variables.scss',
            ),
        ],
        'web.assets_backend': [
            'aciu_base/static/src/scss/aciu_theme.scss',
        ],
        'web.assets_frontend': [
            'aciu_base/static/src/scss/aciu_theme.scss',
            'aciu_base/static/src/scss/aciu_login.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
}
