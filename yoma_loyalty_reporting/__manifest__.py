{
    'name': 'Loyalty Reporting Component',
    'version': '20.0.1.0',
    "category": "Point of Sale",
    "summary": "Loyalty Reporting Component for POS Loyalty",
    "depends": [
        'base',
        'contacts',
        'sale',
        'point_of_sale',
        'yoma_loyalty_membership_management',
        'yoma_loyalty_ext',
    ],
    "data": [
        'security/ir.access.csv',

        # 'views/assets.xml',
        'views/dashboard_menu.xml',
        'views/dashboard_template.xml',



    ],

    "assets": {
        "web.assets_backend": [
            # "yoma_loyalty_reporting/static/src/js/dashboard.js",
            # "yoma_loyalty_reporting/static/src/css/dashboard.css",
        ],
    },

    'development_log': [
        {
            'date': '2026-09-228',
            'developer': 'Zaw Ye Naung',
            'type': 'Function',
            'description': 'Started',
            'version': '19.0.1.0',
        },
    ],

    "installable": True,
    "application": True,
}