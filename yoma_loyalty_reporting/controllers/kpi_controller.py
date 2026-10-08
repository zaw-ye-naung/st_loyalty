from odoo import http
from odoo.http import request
import json


class LoyaltyKPIController(http.Controller):

    @http.route('/loyalty/dashboard/kpi', type='http', auth='user', csrf=False)
    def kpi(self, **kw):

        print("\n\n========== KPI CONTROLLER START ==========")
        print("Incoming params:", kw)

        domain = []

        if kw.get("start_date"):
            domain.append(("create_date", ">=", kw["start_date"] + " 00:00:00"))

        if kw.get("end_date"):
            domain.append(("create_date", "<=", kw["end_date"] + " 23:59:59"))

        print("Domain used:", domain)

        lines = request.env["loyalty.history"].sudo().search(domain)

        print("Total lines fetched:", len(lines))

        earned_lines = lines.filtered(lambda l: l.history_type in ("earn", "earn_red"))
        redeemed_lines = lines.filtered(lambda l: l.history_type in ("redeem", "part_red", "earn_red"))
        expired_lines = lines.filtered(lambda l: l.history_type == "expire")

        print("Earn lines:", len(earned_lines))
        print("Redeem lines:", len(redeemed_lines))
        print("Expire lines:", len(expired_lines))

        earned = sum(earned_lines.mapped("issued"))
        redeemed = sum(redeemed_lines.mapped("used"))
        expired = sum(expired_lines.mapped("used"))

        result = {
            "debug_count": len(lines),
            "earned": earned,
            "redeemed": redeemed,
            "expired": expired,
            "balance": earned - redeemed - expired,
        }

        print("KPI RESULT:", result)
        print("========== KPI CONTROLLER END ==========\n")

        return request.make_response(
            json.dumps(result),
            headers=[("Content-Type", "application/json")]
        )