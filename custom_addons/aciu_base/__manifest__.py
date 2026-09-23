# Part of ACIU Odoo customization.
{
    'name': 'ACIU Base',
    'version': '19.0.1.1.2',
    'category': 'ACIU',
    'summary': 'ACIU organization: Germany central + branches, security groups',
    'description': """
ACIU Base
=========
* Multi-company skeleton: ACIU Germany (central e.V.) + 11 DE branches
* is_registered_ev and branch codes on companies
* Per-branch monthly roll-call fee amount (Berlin-Brandenburg = 5 EUR)
* Branch officers: Treasurer, Financial Secretary, Secretary, Speaker, VP, President
* Central Treasurer/Executive; login branding (ACIU logo)
    """,
    'author': 'ACIU',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/aciu_security.xml',
        'security/ir.model.access.csv',
        'data/aciu_company_data.xml',
        'views/res_company_views.xml',
        'views/aciu_menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
}
