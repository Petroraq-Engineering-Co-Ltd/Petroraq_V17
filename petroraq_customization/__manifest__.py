{
    'name': "petroraq_customization",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Jawaid Iqbal",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['sale', 'web_notify'],

    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'petroraq_customization/static/src/css/style.css',
        ],
    },
}