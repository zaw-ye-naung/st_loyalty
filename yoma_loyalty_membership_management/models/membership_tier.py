from odoo import models, fields


class AlphaMembershipTier(models.Model):
    _name = "membership.tier"
    _description = "Membership Tier"
    _order = "priority asc"

    name = fields.Char(required=True, string="Tier Name")

    code = fields.Char(required=True, string="Tier Code")

    priority = fields.Integer(default=1,string="Priority")

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )

    min_spending = fields.Monetary(
        string="Minimum Spending",
        currency_field="currency_id",
        default=0.0,
    )

    min_points = fields.Integer(default=0,string="Minimum Points")

    multiplier = fields.Float(default=1.0,string="Multiplier")

    active = fields.Boolean(default=True,string="Active")