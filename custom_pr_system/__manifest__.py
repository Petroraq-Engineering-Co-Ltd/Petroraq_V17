{
    'name': 'Custom PR System',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Module for PR and Quotation submission',
    'description': 'Allows end-users and vendors to submit purchase requests and quotations.',
    'author': 'Your Name',
    'depends': ['base'],  # only base is fine
    'data': [
        'security/groups.xml',
        'security/record_rules.xml',
        'security/ir.ui.menu.xml',
        'security/ir.model.access.csv',

        # 'views/templates.xml',
        'views/views.xml',
        # 'views/quotations.xml',

        'data/ir_sequence_data.xml'

    ],
    'installable': True,
    'application': True,  # important to show in Apps
    'auto_install': False,
}
