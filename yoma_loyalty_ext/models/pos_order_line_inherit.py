from odoo import models, fields


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    points_cost = fields.Float(
        string="Points Cost",
        default=0.0,
        help="Points used to pay for this line in partial payment"
    )

    is_reward_line = fields.Boolean(
        string="Is Reward Line",
        default=False,
        help="Indicates if this line was paid with loyalty points"
    )