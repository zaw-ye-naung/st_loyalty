from odoo import http
from odoo.http import request
import json
from collections import defaultdict


class LoyaltyTopCustomersController(http.Controller):

    @http.route(
        '/loyalty/dashboard/top_customers',
        type='http',
        auth='user',
        csrf=False
    )
    def top_customers(self, **kw):

        print("\n" + "=" * 100)
        print("TOP CUSTOMERS FIXED AGGREGATION START")
        print("=" * 100)

        cards = request.env["loyalty.card"].sudo().search([
            ("partner_id", "!=", False)
        ])

        print(f"Cards fetched: {len(cards)}")

        all_history = request.env["loyalty.history"].sudo().search([
            ("card_id", "in", cards.ids)
        ], order="create_date, id")

        print(f"History fetched: {len(all_history)}")

        # ------------------------------------------------------------
        # CUSTOMER MAP
        # ------------------------------------------------------------
        customer_map = defaultdict(lambda: {
            "customer": "",
            "earned": 0.0,
            "redeemed": 0.0,
            "expired": 0.0,
        })

        # ------------------------------------------------------------
        # PROCESS EACH CARD SAFELY
        # ------------------------------------------------------------
        for card in cards:

            partner = card.partner_id

            customer_map[partner.id]["customer"] = partner.name

            lines = all_history.filtered(lambda l: l.card_id.id == card.id)

            print("\n" + "-" * 80)
            print(f"CARD: {card.id} | CUSTOMER: {partner.name}")
            print(f"LINES: {len(lines)}")

            # ========================================================
            # FIX 1: REMOVE DUPLICATE EARN LINES (ROOT CAUSE OF +1)
            # ========================================================
            earn_lines = lines.filtered(lambda l:
                l.history_type in ("earn", "earn_red")
                and (l.issued or 0.0) > 0
            )

            redeem_lines = lines.filtered(lambda l:
                l.history_type in ("redeem", "part_red", "earn_red")
                and (l.used or 0.0) > 0
            )

            expire_lines = lines.filtered(lambda l:
                l.history_type == "expire"
                and (l.used or 0.0) > 0
            )

            # ========================================================
            # FIX 2: DEDUPLICATE EARN ENTRIES (CRITICAL FIX)
            # ========================================================
            seen = set()
            clean_earn = []

            for l in earn_lines:
                key = (l.card_id.id, l.issued, l.create_date)
                if key in seen:
                    print(f"SKIP DUPLICATE EARN LINE: {l.id}")
                    continue
                seen.add(key)
                clean_earn.append(l)

            # ========================================================
            # FINAL CALCULATION
            # ========================================================
            earned = sum(l.issued for l in clean_earn)
            redeemed = sum(l.used for l in redeem_lines)
            expired = sum(l.used for l in expire_lines)

            print("EARN LINES:")
            for l in clean_earn:
                print(f"  ID={l.id} ISSUED={l.issued} TYPE={l.history_type}")

            print("REDEEM LINES:")
            for l in redeem_lines:
                print(f"  ID={l.id} USED={l.used}")

            print("EXPIRE LINES:")
            for l in expire_lines:
                print(f"  ID={l.id} USED={l.used}")

            print(f"RESULT => earned={earned}, redeemed={redeemed}, expired={expired}")

            # ========================================================
            # ACCUMULATE
            # ========================================================
            customer_map[partner.id]["earned"] += earned
            customer_map[partner.id]["redeemed"] += redeemed
            customer_map[partner.id]["expired"] += expired

        # ------------------------------------------------------------
        # FINAL RESULT
        # ------------------------------------------------------------
        result = []

        print("\n" + "=" * 100)
        print("FINAL CUSTOMER RESULT")
        print("=" * 100)

        for pid, data in customer_map.items():

            balance = data["earned"] - data["redeemed"] - data["expired"]

            row = {
                "customer": data["customer"],
                "earned": round(data["earned"], 2),
                "redeemed": round(data["redeemed"], 2),
                "expired": round(data["expired"], 2),
                "balance": round(balance, 2),
            }

            print(row)
            result.append(row)

        result.sort(key=lambda x: x["earned"], reverse=True)
        result = result[:10]

        print("\nTOP 10 FINAL")
        for r in result:
            print(r)

        print("=" * 100)
        print("END CONTROLLER")
        print("=" * 100)

        return request.make_response(
            json.dumps(result),
            headers=[("Content-Type", "application/json")]
        )