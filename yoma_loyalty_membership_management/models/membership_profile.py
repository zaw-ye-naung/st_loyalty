import base64
from io import BytesIO
import qrcode

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MembershipProfile(models.Model):
    _name = "membership.profile"
    _description = "Membership Profile"
    _rec_name = "partner_id"

    _sql_constraints = [
        (
            "uniq_partner_profile",
            "unique(partner_id)",
            "A partner can only have one membership profile."
        ),
        (
            "uniq_member_code",
            "unique(member_code)",
            "Member code must be unique."
        ),
    ]

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        string="Partner",
        ondelete="cascade",
        index=True,
    )

    birthday = fields.Date(
        string="Birthday",
        compute="_compute_birthday",
        store=True,
    )

    member_code = fields.Char(
        string="Member Code",
        copy=False,
        readonly=True,
        index=True,
    )

    membership_status = fields.Selection(
        [
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("expired", "Expired"),
        ],
        default="active",
        string="Membership Status",
    )

    # QR is now derived from partner barcode
    qr_code = fields.Char(
        string="QR Code",
        compute="_compute_qr_code",
        store=True,
        index=True,
    )

    qr_image = fields.Binary(
        string="QR Image",
        compute="_compute_qr_image",
        store=False
    )

    member_since = fields.Datetime(
        string="Member Since",
        default=fields.Datetime.now,
    )

    tier_id = fields.Many2one(
        "membership.tier",
        string="Tier",
        compute="_compute_tier_id",
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    total_spent = fields.Monetary(
        string="Total Spent",
        compute="_compute_totals",
        currency_field="currency_id",
        store=True,
    )

    total_orders = fields.Integer(
        string="Total Orders",
        compute="_compute_totals",
        store=True,
    )

    last_activity_date = fields.Datetime(
        string="Last Activity Date",
        compute="_compute_totals",
        store=True,
    )

    points_balance = fields.Float(
        string="Points Balance",
        compute="_compute_points_balance",
        store=False,
        digits=(16, 2),
    )

    loyalty_card_id = fields.One2many(
        "loyalty.card",
        "partner_id",
        string="Loyalty Cards"
    )

    @api.depends("partner_id")
    def _compute_points_balance(self):
        for rec in self:

            rec.points_balance = 0.0

            if not rec.partner_id:
                continue

            # SEARCH CARD FROM PARTNER
            card = self.env["loyalty.card"].search([
                ("partner_id", "=", rec.partner_id.id)
            ], limit=1)

            if not card:
                continue

            # COMPUTE BALANCE FROM HISTORY
            self.env.cr.execute("""
                SELECT COALESCE(SUM(issued) - SUM(used), 0)
                FROM loyalty_history
                WHERE card_id = %s
            """, (card.id,))

            result = self.env.cr.fetchone()

            rec.points_balance = result[0] if result else 0.0

    # -------------------------------------------------
    # CREATE
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("member_code"):
                vals["member_code"] = self._generate_member_code()

        records = super().create(vals_list)

        for rec in records:
            if rec.partner_id:
                rec.partner_id.write({
                    "membership_profile_id": rec.id
                })

        return records

    # -------------------------------------------------
    # SEQUENCE
    def _generate_member_code(self):
        return self.env['ir.sequence'].next_by_code('membership.profile')

    # -------------------------------------------------
    # QR CODE (from partner barcode)
    @api.depends("partner_id.barcode")
    def _compute_qr_code(self):
        for rec in self:
            rec.qr_code = rec.partner_id.barcode or False

    @api.depends("partner_id.birthday")
    def _compute_birthday(self):
        for rec in self:
            rec.birthday = rec.partner_id.birthday or False

    # -------------------------------------------------
    # QR IMAGE
    @api.depends("partner_id.barcode")
    def _compute_qr_image(self):
        for rec in self:
            qr_value = rec.partner_id.barcode

            if not qr_value:
                rec.qr_image = False
                continue

            qr = qrcode.QRCode(
                version=1,
                box_size=4,
                border=2
            )
            qr.add_data(qr_value)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")

            rec.qr_image = base64.b64encode(buffer.getvalue())

    # -------------------------------------------------
    # TIER COMPUTATION
    @api.depends("total_spent", "currency_id")
    def _compute_tier_id(self):
        """
        Compute the appropriate tier based on total_spent and min_spending.
        """
        for rec in self:
            # Skip if no total_spent (avoid unnecessary searches)
            if rec.total_spent is None:
                rec.tier_id = False
                continue

            # Find the highest priority tier where min_spending <= total_spent
            tiers = self.env["membership.tier"].search([
                ("active", "=", True),
                ("min_spending", "<=", rec.total_spent),
            ], order="min_spending desc, priority desc", limit=1)

            if tiers:
                rec.tier_id = tiers[0].id
            else:
                # Set a default tier for users with no spending
                default_tier = self.env["membership.tier"].search([
                    ("active", "=", True),
                    ("min_spending", "=", 0),
                ], limit=1)
                rec.tier_id = default_tier.id if default_tier else False

    # -------------------------------------------------
    # TOTALS (POS) - IMPROVED WITH BETTER DEPENDENCIES
    @api.depends("partner_id", "partner_id.pos_order_ids")
    def _compute_totals(self):
        """
        Compute totals based on POS orders.
        This will automatically trigger when POS orders are created/modified/deleted
        because of the dependency on partner_id.pos_order_ids.
        """
        for rec in self:
            if not rec.partner_id:
                rec.total_orders = 0
                rec.total_spent = 0.0
                rec.last_activity_date = False
                continue

            # Get all paid/done/invoiced POS orders for this partner
            orders = rec.partner_id.pos_order_ids.filtered(
                lambda o: o.state in ['paid', 'done', 'invoiced']
            )

            rec.total_orders = len(orders)
            rec.total_spent = sum(orders.mapped("amount_total"))

            rec.last_activity_date = (
                max(orders.mapped("date_order"))
                if orders else False
            )

    # -------------------------------------------------
    # CONSTRAINTS
    @api.constrains("partner_id")
    def _check_partner_unique(self):
        for rec in self:
            if rec.partner_id and self.search_count([
                ("partner_id", "=", rec.partner_id.id),
                ("id", "!=", rec.id),
            ]):
                raise ValidationError(
                    "This partner already has a membership profile."
                )

    # -------------------------------------------------
    # MANUAL UPDATE METHOD
    def action_update_totals_and_tier(self):
        """
        Manually trigger update of totals and tier for selected profiles
        """
        for rec in self:
            rec._compute_totals()
            rec._compute_tier_id()
        return True