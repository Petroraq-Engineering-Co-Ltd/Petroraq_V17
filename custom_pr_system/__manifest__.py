{
    'name': 'Custom PR System',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Module for PR and Quotation submission',
    'description': 'Allows end-users and vendors to submit purchase requests and quotations.',
    'author': 'Your Name',
    'depends': ['base', 'stock', 'purchase'],  # only base is fine
    'data': [
        'security/groups.xml',
        'security/record_rules.xml',
        'security/ir.ui.menu.xml',
        'security/ir.model.access.csv',

        'views/templates.xml',
        'views/views.xml',
        'views/inventory.xml',
        'views/remarks_popup.xml',
        # 'views/quotations.xml',

        'data/ir_sequence_data.xml'

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
