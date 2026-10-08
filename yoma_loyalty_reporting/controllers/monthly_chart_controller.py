from odoo import http
from odoo.http import request
import json


class LoyaltyDashboardChartController(http.Controller):

    @http.route('/loyalty/dashboard/monthly', type='http', auth='user', csrf=False)
    def monthly(self, **kw):

        print("\n\n========== MONTHLY CONTROLLER START ==========")

        histories = request.env["loyalty.history"].sudo().search([], order="create_date")

        print("Total history lines:", len(histories))

        data = {}

        for line in histories:

            if not line.create_date:
                continue

            month = line.create_date.strftime("%Y-%m")

            if month not in data:
                data[month] = {"earned": 0, "redeemed": 0, "expired": 0}

            if line.history_type in ("earn", "earn_red"):
                data[month]["earned"] += (line.issued or 0)

            if line.history_type in ("redeem", "part_red", "earn_red"):
                data[month]["redeemed"] += (line.used or 0)

            if line.history_type == "expire":
                data[month]["expired"] += (line.used or 0)

        print("Monthly aggregated keys:", list(data.keys()))
        print("Monthly data:", data)
        print("========== MONTHLY CONTROLLER END ==========\n")

        return request.make_response(
            json.dumps(data),
            headers=[("Content-Type", "application/json")]
        )