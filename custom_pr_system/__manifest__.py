{
    'name': 'Custom PR System',
    'version': '17.0.1.0.0',   # match migrations folder
    # 'version': '1.0',
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
        'views/grn_report.xml',
        # 'views/quotations.xml',

        'data/ir_sequence_data.xml',
        'data/custom_unit_data.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
