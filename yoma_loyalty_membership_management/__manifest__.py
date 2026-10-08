{
    'name': 'Loyalty Membership Management Component',
    'version': '20.0.1.0',
    "category": "Point of Sale",
    "summary": "Loyalty Membership Management Component for POS",
    "depends": [
        "base",
        "contacts",
        "sale",
        "point_of_sale",
        "loyalty",
    ],
    "data": [
        "security/ir.access.csv",

        "data/sequence.xml",
        "data/tier_data.xml",

        "views/res_partner_views.xml",
        "views/membership_profile_views.xml",
        "views/membership_tier_views.xml",
    ],

    'assets': {
        'point_of_sale._assets_pos': [
        ],
    },

    'development_log': [
        {
            'date': '2026-09-28',
            'developer': 'Zaw Ye Naung',
            'type': 'Function',
            'description': 'Started',
            'version': '19.0.1.0',
        },
    ],

    "installable": True,
    "application": True,
}