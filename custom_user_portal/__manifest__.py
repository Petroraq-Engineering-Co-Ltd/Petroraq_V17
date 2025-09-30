# -*- coding: utf-8 -*-
{
    'name': "custom_user_portal",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
    Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'portal', 'product', 'hr', 'mail', 'web', 'purchase', 'bus', 'project', 'custom_pr_system'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/purchase_requisition_security.xml',
        'security/quotation.xml',
        
        'views/views.xml',
        'views/templates.xml',
        'views/portal_pr_form_template.xml',
        'views/quotation.xml',
        'views/pr_odoo_ui.xml',
        'views/portal_quotation.xml',
        'views/project_view.xml',
        'views/pr_portal_view.xml',
        'views/cash_odoo_ui.xml',
        'views/rfq_vendor.xml',

        'data/ir_sequence_data.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
    'web.assets_backend': [
            'custom_user_portal/static/src/css/style.scss'
        ]
    },
    'auto_install': False,
    'application': True,

}

