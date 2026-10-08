from odoo import models, fields

class LoyaltyCard(models.Model):
    _inherit = "loyalty.card"

    validity_days = fields.Integer(
        string="Points Validity",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_int(
            "loyalty.validity_days", 365
        ),
        help="Number of days loyalty points are valid."
    )