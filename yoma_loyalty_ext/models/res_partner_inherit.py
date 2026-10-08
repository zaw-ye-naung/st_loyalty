from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    loyalty_point_balance = fields.Integer(
        compute="_compute_loyalty_balance",
        string="Loyalty Points"
    )

    # Optional: if you want to sync from loyalty.card
    loyalty_card_id = fields.Many2one(
        "loyalty.card",
        compute="_compute_loyalty_balance",
        string="Loyalty Card"
    )

    def _compute_loyalty_balance(self):
        LoyaltyCard = self.env["loyalty.card"]

        for partner in self:

            # -------------------------------------------------
            # 1. Get or find loyalty card
            # -------------------------------------------------
            card = LoyaltyCard.search([
                ("partner_id", "=", partner.id)
            ], limit=1)

            partner.loyalty_card_id = card

            # -------------------------------------------------
            # 2. Use loyalty.card as SINGLE source of truth
            # -------------------------------------------------
            if card:
                partner.loyalty_point_balance = card.points or 0
            else:
                partner.loyalty_point_balance = 0