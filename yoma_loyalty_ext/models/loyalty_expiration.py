from odoo import models, api, fields


class LoyaltyExpiration(models.Model):
    _name = "loyalty.expiration"
    _description = "Loyalty Expiration Engine"

    @api.model
    def run_expiration(self):

        today = fields.Date.today()

        histories = self.env["loyalty.history"].search([
            ("history_type", "=", "earn"),
            ("is_expired", "=", False),
            ("remaining_points", ">", 0),
            ("expiration_date", "<=", today),
        ])

        expire_vals = []
        to_mark_expired = []

        for history in histories:

            if not history.card_id:
                continue

            points_to_expire = history.remaining_points

            if points_to_expire <= 0:
                to_mark_expired.append(history.id)
                continue

            # ❌ DO NOT touch card.points

            expire_vals.append({
                "card_id": history.card_id.id,
                "points": -points_to_expire,
                "history_type": "expire",
                "expiration_date": today,
                "remaining_points": 0,
                "is_expired": True,
            })

            to_mark_expired.append(history.id)

        # batch insert (IMPORTANT)
        if expire_vals:
            self.env["loyalty.history"].create(expire_vals)

        # batch update flags
        if to_mark_expired:
            self.env["loyalty.history"].browse(to_mark_expired).write({
                "remaining_points": 0,
                "is_expired": True
            })