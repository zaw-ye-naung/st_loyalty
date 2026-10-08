from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LoyaltyReward(models.Model):
    _inherit = "loyalty.reward"

    reward_type = fields.Selection(
        selection_add=[
            ('partial_redeem', 'Partial Redeem'),
        ],
        ondelete={'partial_redeem': 'set default'}
    )

    points_to_currency_rate = fields.Monetary(
        string="One Point Equivalence",
        currency_field="currency_id",
        default=1.0,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )

    @api.onchange('reward_type')
    def _onchange_reward_type(self):
        for rec in self:

            if rec.reward_type == 'partial_redeem':
                rec.points_to_currency_rate = 1.0
                rec.required_points = 0.1

            else:
                rec.points_to_currency_rate = False
                rec.required_points = 0.0

    # -------------------------------------------------
    # SAFETY CHECK
    # -------------------------------------------------
    @api.constrains('reward_type', 'points_to_currency_rate')
    def _check_partial_redeem_fields(self):
        for rec in self:

            if rec.reward_type != 'partial_redeem':
                if rec.points_to_currency_rate:
                    raise ValidationError(
                        "Rate is only allowed for Partial Redeem rewards."
                    )