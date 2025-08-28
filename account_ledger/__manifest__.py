# -*- coding: utf-8 -*-

{
    'name': 'Account Ledger',
    'summary': """Account Ledger""",
    'version': '0.1',
    'description': """This module allows the user to view detailed ledger
            for a specific account and all the journal entries level detailed information
            can be drawn using this report
            """,
    'author': 'Arure Technologies',
    'company': 'Arure Technologies',
    'website': 'http://www.arure.tech/',
    'category': 'Accounting',
    'depends': ['pr_hr_account', 'eg_asset_management'],
    'price': '17.0',
    'license': 'OPL-1',
    'data': [
        'security/ir.model.access.csv',
        # 'views/dynamic_report_template.xml',
        'wizard/account_ledger.xml',
        'wizard/vat_ledger_report_wizard.xml',
        'wizard/custom_dynamic_ledger_report_wizard.xml',
        'report/account_ledger_report.xml',
        'report/vat_ledger_report.xml',
        'report/custom_dynamic_ledger_report.xml',
        'report/account_ledger_xlsx_report.xml',
        'report/vat_ledger_xlsx_report.xml'
    ],
    # 'assets': {
    #         'web.assets_backend': [
    #             'account_ledger/static/src/js/dynamic_balance_report.js',
    #             'account_ledger/static/src/xml/dynamic_balance_report.xml',
    #         ],
    #     },
    'qweb': [],
    'images': ['static/description/banner.jpeg'],
    'demo': [],        
    'installable': True,
    'application': True,
    'auto_install': False,

}