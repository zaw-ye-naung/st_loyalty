import re
from datetime import timedelta

from odoo import models, fields, api

class LoyaltyHistory(models.Model):
    _inherit = "loyalty.history"

    order_id = fields.Many2one(
        "pos.order",
        string="POS Order",
        index=True,
    )

    expiration_date = fields.Datetime(
        string="Exp Date",
        compute="_compute_expiration_date",
        store=True,
        index=True,
        readonly=False
    )

    is_expired = fields.Boolean(default=False, index=True)

    history_type = fields.Selection([
        ("earn", "Earn"),
        ("redeem", "Fixed Redeem"),
        ("refund", "Refund"),
        ("reward_refund", "Reward Refund"),
        ("part_refund","Partial Refund"),
        ("expire", "Expire"),
        ("earn_red", "Earn and Redeem"),
        ("part_red", "Partial Redeem"),
        ],
        string="Transaction Type",
        compute="_compute_history_type",
        store=True,
        default="earn",
        index=True
    )

    balance = fields.Float(
        string="Balance",
        compute="_compute_balance",
        digits=(16, 2),
        store=False,
    )

    is_manual_type = fields.Boolean(
        string="Manual History Type",
        default=False,
        help="If checked, system will not override history_type",
    )

    @api.depends("card_id", "issued", "used", "create_date")
    def _compute_balance(self):
        for record in self:
            if not record.card_id:
                record.balance = 0.0
                continue

            lines = self.search(
                [("card_id", "=", record.card_id.id)],
                order="create_date, id"
            )

            running = 0.0

            for line in lines:
                running += (line.issued or 0.0)
                running -= (line.used or 0.0)

                if line.id == record.id:
                    record.balance = running
                    break

    @api.depends("issued", "used")
    def _compute_history_type(self):
        for record in self:
            if record.is_manual_type:
                continue

            if record.history_type in ("expire", "refund"):
                continue

            if record.issued and record.used:
                record.history_type = "earn_red"
            elif record.used:
                record.history_type = "redeem"
            elif record.issued:
                record.history_type = "earn"
            else:
                record.history_type = "earn"

    @api.depends("issued", "card_id.validity_days", "create_date", "history_type")
    def _compute_expiration_date(self):
        for record in self:
            if record.history_type not in ("earn","earn_red"):
                record.expiration_date = False
                continue

            base_date = record.create_date or fields.Datetime.now()
            validity = record.card_id.validity_days or 0

            record.expiration_date = base_date + timedelta(days=validity)

    def _cron_expire_loyalty_points(self):
        today = fields.Datetime.now()

        earn_lines = self.search([
            ("history_type", "in", ["earn","earn_red"]),
            ("expiration_date", "<=", today),
            ("is_expired", "=", False),
        ], order="create_date, id")

        for line in earn_lines:
            issued = line.issued or 0.0

            previous_earn_lines = self.search([
                ("card_id", "=", line.card_id.id),
                ("history_type", "in", ["earn","earn_red"]),
                ("create_date", "<=", line.create_date),
            ], order="create_date, id")

            previous_earn_total = sum(previous_earn_lines.mapped("issued"))

            redeem_lines = self.search([
                ("card_id", "=", line.card_id.id),
                ("used", ">", 0),
            ], order="create_date, id")

            total_redeemed = sum(redeem_lines.mapped("used"))

            consumed = max(
                0.0,
                total_redeemed - (previous_earn_total - issued)
            )

            remaining = issued - consumed

            if remaining <= 0:
                line.is_expired = True
                continue

            self.create({
                "card_id": line.card_id.id,
                "issued": 0.0,
                "used": remaining,
                "history_type": "expire",
                "description": f"Expired {remaining} points",
            })

            line.card_id.points = line.card_id.points - remaining
            line.is_expired = True