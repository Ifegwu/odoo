# Part of ACIU Odoo customization.
{
    'name': 'ACIU Base',
    'version': '19.0.1.1.0',
    'category': 'ACIU',
    'summary': 'ACIU organization: Germany central + branches, security groups',
    'description': """
ACIU Base
=========
* Multi-company skeleton: ACIU Germany (central e.V.) + 11 DE branches
* is_registered_ev and branch codes on companies
* Per-branch monthly roll-call fee amount (Berlin-Brandenburg = 5 EUR)
* Security groups: Member, Branch Treasurer/Leader, Central Treasurer/Executive
* Login branding: ACIU logo on companies (platform login logo)
    """,
    'author': 'ACIU',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/aciu_security.xml',
        'data/aciu_company_data.xml',
        'views/res_company_views.xml',
        'views/aciu_menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
}
