{
    'name': 'GoDaddy API Integration',
    'version': '1.0',
    'summary': 'Integrate GoDaddy Domain API with Odoo',
    'description': 'This module allows users to interact with the GoDaddy API for domain management directly from Odoo.',
    'author': 'He Zhongqing',
    'website': 'https://yourwebsite.com',
    'category': 'Tools',
    'depends': ['base'],  # 如果需要与销售、网站等模块集成，可以添加对应依赖
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}