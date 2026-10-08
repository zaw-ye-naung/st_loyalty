from odoo import models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    type = fields.Selection(
        selection_add=[
            ('loyalty_points', 'Loyalty Points')
        ],
        ondelete={'loyalty_points': 'cascade'}
    )

    is_loyalty_points = fields.Boolean(
        string="Use Loyalty Points"
    )

    loyalty_payment_available = fields.Boolean(
        compute="_compute_loyalty_payment_available"
    )

    @api.depends()
    def _compute_loyalty_payment_available(self):

        reward_exists = bool(
            self.env["loyalty.reward"].search_count([
                ("reward_type", "=", "partial_redeem")
            ])
        )

        for method in self:
            if method.is_loyalty_points:
                method.loyalty_payment_available = reward_exists
            else:
                method.loyalty_payment_available = True