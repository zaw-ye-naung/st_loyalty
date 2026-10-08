from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()

        reward_exists = bool(
            self.env["loyalty.reward"].search_count([
                ("reward_type", "=", "partial_redeem")
            ])
        )

        if not reward_exists:
            result["search_params"]["domain"] = [
                ("is_loyalty_points", "=", False)
            ]

        return result