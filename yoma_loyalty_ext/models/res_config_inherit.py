from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    loyalty_validity_days = fields.Integer(string="Loyalty Points Validity (Days)")

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "loyalty.validity_days",
            self.loyalty_validity_days or 365
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()

        res.update(
            loyalty_validity_days=int(
                params.get_param("loyalty.validity_days", default=365)
            )
        )
        return res