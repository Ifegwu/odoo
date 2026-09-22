# Part of ACIU Odoo customization.
{
    'name': 'ACIU Membership',
    'version': '19.0.1.1.0',
    'category': 'ACIU',
    'summary': 'ACIU member profiles and soft open-debt tracking',
    'description': """
ACIU Membership
===============
* Member flag and profile fields on contacts
* Home branch (ACIU company); contacts nested under branch in Contacts
* Soft open-debt display (never hard-blocks membership)
    """,
    'author': 'ACIU',
    'license': 'LGPL-3',
    'depends': ['aciu_base', 'contacts', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/aciu_membership_rules.xml',
        'views/res_partner_views.xml',
        'views/aciu_membership_menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
}
