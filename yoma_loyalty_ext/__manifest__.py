{
    'name': 'Loyalty Extension Component',
    'version': '20.0.1.0',
    "category": "Point of Sale",
    "summary": "Loyalty Extension Component for POS Loyalty",
    "depends": [
        'base',
        'contacts',
        'sale',
        'point_of_sale',
        'yoma_loyalty_membership_management',
    ],
    "data": [
        'security/ir.access.csv',
        # 'data/pos_payment_method_data.xml',
        'data/cron.xml',

        # Points Transaction Ledger/ Life Cycle
        'views/res_partner_views_inherit.xml',
        'views/loyalty_transaction_views.xml',
        'views/loyalty_history_views_inherit.xml',
        'views/loyalty_card_views_inherit.xml',
        'views/loyalty_reward_views_inherit.xml',

        # Partial Redeeming
        'views/res_config_views_inherit.xml',
        'views/pos_payment_method_views_inherit.xml',

    ],

    'assets': {
        'point_of_sale._assets_pos': [
            # 'yoma_loyalty_ext/static/src/js/payment_screen.js',
            # 'yoma_loyalty_ext/static/src/xml/payment_screen_inherit.xml',
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