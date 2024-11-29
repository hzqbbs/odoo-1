# -*- coding: utf-8 -*-
{
    'name': 'Sale Order API',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Custom API for creating sale orders',
    'description': """
        This module provides an API interface for creating sale orders programmatically.
    """,
    'depends': ['sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}