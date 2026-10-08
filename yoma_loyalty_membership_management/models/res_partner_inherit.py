from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    birthday = fields.Date(string="Birthday")
    
    membership_profile_id = fields.Many2one(
        "membership.profile",
        string="Membership Profile",
        copy=False,
        ondelete="set null",
    )

    loyalty_partner = fields.Boolean(
        string="Loyalty Partner",
        compute="_compute_loyalty_partner",
        readonly=True,
        store=True
    )

    membership_status = fields.Selection(
        related="membership_profile_id.membership_status",
        store=True,
        readonly=True,
        string="Membership Status",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("barcode"):
                seq = self.env["ir.sequence"].next_by_code(
                    "res.partner.barcode"
                )
                vals["barcode"] = f"042{seq}"

        return super().create(vals_list)

    @api.depends("membership_profile_id")
    def _compute_loyalty_partner(self):
        for partner in self:
            partner.loyalty_partner = True if partner.membership_profile_id else False

    @api.constrains("membership_profile_id")
    def _check_membership_profile(self):
        for partner in self:
            if partner.membership_profile_id:
                if partner.membership_profile_id.partner_id != partner:
                    raise ValidationError(
                        "The selected membership profile is not the same as the selected partner"
                    )

    @staticmethod
    def pos_barcode_lookup(env, barcode):
        """
        Central lookup used by POS for partner scanning.
        Supports both barcode and qr_code.
        """
        Partner = env["res.partner"]

        partner = Partner.search([("barcode", "=", barcode)], limit=1)
        if partner:
            return partner

        partner = Partner.search([("qr_code", "=", barcode)], limit=1)
        if partner:
            return partner

        return Partner.browse()