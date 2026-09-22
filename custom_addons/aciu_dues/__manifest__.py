# Part of ACIU Odoo customization.
{
    'name': 'ACIU Dues',
    'version': '19.0.1.0.0',
    'category': 'ACIU',
    'summary': 'ACIU annual dues, roll-call fees, projects and burial levies',
    'description': """
ACIU Dues
=========
* Annual membership due product (€20)
* Monthly roll-call fee product (amount from branch company; Berlin = €5)
* Soft debt: unpaid charges never block membership
* Scaffold for project contributions and ad-hoc burial levy campaigns
    """,
    'author': 'ACIU',
    'license': 'LGPL-3',
    'depends': ['aciu_membership', 'account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/aciu_product_data.xml',
        'views/aciu_levy_campaign_views.xml',
        'wizard/aciu_generate_dues_views.xml',
        'views/aciu_dues_menus.xml',
    ],
    'installable': True,
}
