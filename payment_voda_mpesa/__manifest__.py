# -*- coding: utf-8 -*-
{
    'name': "Vodacom Mpesa Payment Acquirer",
    'summary': 'A payment gateway to accept online payments via M-pesa',
    'description': 'A payment gateway to accept online payments via M-pesa',
    'maintainer': 'Kashoke Tech',
    'company': 'Kashoke Tech',
    'author': 'Kashoke Tech',
    # 'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Invoicing & Payments',
    'version': '15.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['payment'],
    'price': 270,
    'currency': 'USD',
    'license': "OPL-1",
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/payment_mpesa_templates.xml',
        'views/payment_views.xml',
        'data/payment_icon_data.xml',
        'data/payment_acquirer_data.xml'
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'payment_mpesa/static/src/js/payment_form.js',
        ],
    },
}
