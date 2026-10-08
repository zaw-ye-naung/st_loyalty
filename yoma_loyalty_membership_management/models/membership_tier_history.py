from odoo import models, fields


class AlphaMembershipTierHistory(models.Model):
    _name = "membership.tier.history"
    _description = "Membership Tier History"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        string="Partner",
    )

    old_tier_id = fields.Many2one(
        "membership.tier",
        string="Old Tier",
    )

    new_tier_id = fields.Many2one(
        "membership.tier",
        string="New Tier",
    )

    changed_at = fields.Datetime(
        string="Changed At",
        default=fields.Datetime.now
    )

    reason = fields.Char(string="Reason")