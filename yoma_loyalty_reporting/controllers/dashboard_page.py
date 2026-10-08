from odoo import http
from odoo.http import request


class LoyaltyDashboardPage(http.Controller):

    @http.route(
        '/loyalty/dashboard',
        type='http',
        auth='user'
    )
    def dashboard_page(self, **kw):

        return request.render(
            "yoma_loyalty_reporting.dashboard_template",
            {}
        )