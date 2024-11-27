# auto_assign_sales_purchase/__manifest__.py
{
    'name': 'Company Member Management',
    'version': '1.0',
    'category': 'Customization',
    'summary': 'Automatically assign sales, purchase, and website groups to new users',
    'description': """
        This module automatically assigns the sales and purchase groups to newly created users.
    """,
    'author': 'He Zhongqing',
    'depends': ['base', 'portal', 'website', 'auth_signup'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/company_member_approval_views.xml',
        'views/res_users_views.xml',
        'views/portal_my_home_inherit.xml',
        'views/company_select_form.xml',
    ],
    'installable': True,
    'application': False,
}