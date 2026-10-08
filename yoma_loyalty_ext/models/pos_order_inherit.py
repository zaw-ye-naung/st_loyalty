from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = "pos.order"

    loyalty_points_used = fields.Float(default=0.0)
    reward_id = fields.Many2one("loyalty.reward")
    loyalty_refund_processed = fields.Boolean(default=False)
    loyalty_payment_processed = fields.Boolean(default=False)

    original_order_id = fields.Many2one(
        'pos.order',
        string='Original Order',
        help='Original order that this order is refunding'
    )

    @api.model
    def _process_order(self, order, existing_order):
        # Validate loyalty BEFORE Odoo creates the POS order
        self._validate_raw_pos_order_loyalty(order)

        # Let Odoo create the order
        pos_order_id = super()._process_order(
            order,
            existing_order,
        )

        if not pos_order_id:
            return pos_order_id

        pos_order = self.browse(pos_order_id)

        if pos_order.exists():
            pos_order._process_loyalty()

        # Odoo 19 expects the integer ID
        return pos_order_id

    def _validate_raw_pos_order_loyalty(self, order):
        if not isinstance(order, dict):
            return

        loyalty_payment_lines = []

        for payment_command in order.get("payment_ids") or []:

            payment_values = False

            if isinstance(payment_command, (list, tuple)):
                if len(payment_command) >= 3:
                    payment_values = payment_command[2]

            elif isinstance(payment_command, dict):
                payment_values = payment_command

            if not isinstance(payment_values, dict):
                continue

            payment_method_id = payment_values.get(
                "payment_method_id"
            )

            if isinstance(payment_method_id, (list, tuple)):
                payment_method_id = (
                    payment_method_id[0]
                    if payment_method_id
                    else False
                )

            if not payment_method_id:
                continue

            payment_method = self.env[
                "pos.payment.method"
            ].browse(
                int(payment_method_id)
            ).exists()

            if not payment_method:
                continue

            if not payment_method.is_loyalty_points:
                continue

            try:
                amount = float(
                    payment_values.get("amount") or 0.0
                )
            except (TypeError, ValueError):
                raise ValidationError(
                    "Invalid loyalty payment amount."
                )

            if amount == 0:
                continue

            loyalty_payment_lines.append(amount)

        # No loyalty payment → no loyalty validation required
        if not loyalty_payment_lines:
            return

        # ---------------------------------------------------------
        # CUSTOMER
        # ---------------------------------------------------------

        partner_id = order.get("partner_id")

        if isinstance(partner_id, (list, tuple)):
            partner_id = (
                partner_id[0]
                if partner_id
                else False
            )

        if not partner_id:
            raise ValidationError(
                "Select customer first."
            )

        partner = self.env[
            "res.partner"
        ].browse(
            int(partner_id)
        ).exists()

        if not partner:
            raise ValidationError(
                "The selected customer does not exist."
            )

        # ---------------------------------------------------------
        # LOYALTY ELIGIBILITY
        # ---------------------------------------------------------

        if not partner.loyalty_partner:
            raise ValidationError(
                "Customer not eligible."
            )

        # ---------------------------------------------------------
        # LOYALTY CARD
        # ---------------------------------------------------------

        card = partner.loyalty_card_id

        if not card:
            raise ValidationError(
                "The customer does not have a loyalty card."
            )

        # ---------------------------------------------------------
        # REWARD
        # ---------------------------------------------------------

        reward = self.env[
            "loyalty.reward"
        ].search(
            [
                ("reward_type", "=", "partial_redeem"),
            ],
            limit=1,
        )

        if not reward:
            raise ValidationError(
                "No Partial Redeem reward configured."
            )

        # ---------------------------------------------------------
        # RATE
        # ---------------------------------------------------------

        rate = reward.points_to_currency_rate or 1.0

        if rate <= 0:
            raise ValidationError(
                "The loyalty points-to-currency rate "
                "must be greater than zero."
            )

        # ---------------------------------------------------------
        # REQUIRED POINTS
        # ---------------------------------------------------------

        total_points_required = 0.0

        for amount in loyalty_payment_lines:

            if amount > 0:
                total_points_required += round(
                    amount / rate,
                    2,
                )

        if total_points_required <= 0:
            return

        # ---------------------------------------------------------
        # BALANCE CHECK
        # ---------------------------------------------------------

        if card.points < total_points_required:
            raise ValidationError(
                "Not enough points.\n\n"
                "Required: %.2f points\n"
                "Available: %.2f points"
                % (
                    total_points_required,
                    card.points,
                )
            )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------
    @api.model
    def create(self, vals):
        order = super().create(vals)

        reward = self.env["loyalty.reward"].search([
            ("reward_type", "=", "partial_redeem")
        ], limit=1)

        order.reward_id = reward.id if reward else False
        return order

    # ---------------------------------------------------------
    # SAFE ENTRY POINT (CRITICAL FIX)
    # ---------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        # Trigger on finalization (covers backend refunds too)
        if vals.get("state") in ("paid", "done"):
            for order in self:
                order._process_loyalty()

        return res

# ---------------------------------------------------------
    # MAIN DISPATCHER
    # ---------------------------------------------------------
    def _process_loyalty(self):
        for order in self:
            card = order.partner_id.loyalty_card_id if order.partner_id else False
            if not card:
                continue

            reward = order.reward_id
            rate = reward.points_to_currency_rate if reward else 1

            # Refund restore (reward lines etc.)
            reward_restore = order._restore_reward_points_on_refund(card)
            if reward_restore:
                card.points += reward_restore

            # Refund logic
            if order.amount_total < 0 and not order.loyalty_refund_processed:
                order._process_loyalty_refund(card, rate)

            # Payment logic
            if order.amount_total >= 0 and not order.loyalty_payment_processed:
                order._process_loyalty_payment(card, rate)

    # ---------------------------------------------------------
    # REFUND LOGIC
    # ---------------------------------------------------------
    def _process_loyalty_refund(self, card, rate):
        for order in self:

            product_refund_points = 0.0
            partial_payment_refund_points = 0.0
            processed_orders = {}

            for line in order.lines:
                if line.qty >= 0:
                    continue

                original = line.refunded_orderline_id
                if not original:
                    continue

                # -------------------------------------------------
                # FIX: reward lines are handled by
                # _restore_reward_points_on_refund. Skip them here
                # so the points are not credited twice.
                # -------------------------------------------------
                if (
                        getattr(original, "is_reward_line", False)
                        or getattr(original, "points_cost", 0)
                ):
                    continue

                original_order = original.order_id

                if original_order.id in processed_orders:
                    continue

                processed_orders[original_order.id] = True

                earn_lines = self.env["loyalty.history"].search([
                    ("card_id", "=", card.id),
                    ("history_type", "in", ("earn", "earn_red")),
                    ("order_id", "=", original_order.id),
                ])

                total_earned_points = sum(earn_lines.mapped("issued"))
                if total_earned_points <= 0:
                    continue

                current_refund_amount = abs(line.price_subtotal_incl)

                previous_refunded_amount = self._get_total_refunded_amount(
                    original_order,
                    exclude_current_order=order
                )

                remaining = original_order.amount_total - (
                        previous_refunded_amount + current_refund_amount
                )

                min_amount = self._get_minimum_amount_for_order(original_order)
                reversed_before = self._get_total_reversed_points(original_order, card)

                if min_amount > 0 and remaining < min_amount:
                    reversed_points = total_earned_points - reversed_before
                else:
                    if not original_order.amount_total:
                        continue
                    reversed_points = (
                                              total_earned_points * current_refund_amount
                                      ) / original_order.amount_total

                product_refund_points += reversed_points

                self.env["loyalty.history"].create({
                    "card_id": card.id,
                    "issued": 0.0,
                    "used": reversed_points,
                    "history_type": "refund",
                    "is_manual_type": True,
                    "description": f"Product Return Refunded {reversed_points}",
                    "order_id": original_order.id,
                })

            # -------------------------
            # PARTIAL PAYMENT REFUND
            # -------------------------
            refund_points = 0.0

            for payment in order.payment_ids:
                method = payment.payment_method_id

                if not method.is_loyalty_points:
                    continue

                refund_points += abs(payment.amount) / rate

            if refund_points:
                partial_payment_refund_points += refund_points

                self.env["loyalty.history"].create({
                    "card_id": card.id,
                    "issued": refund_points,
                    "used": 0.0,
                    "history_type": "part_refund",
                    "is_manual_type": True,
                    "description": "Partial Payment Refund",
                    "order_id": order.id,
                })

            # APPLY
            # NOTE: reward refund is NOT applied here — it is handled
            # exclusively by _restore_reward_points_on_refund.
            if product_refund_points:
                card.points -= product_refund_points

            if partial_payment_refund_points:
                card.points += partial_payment_refund_points

            order.loyalty_refund_processed = True

    # ---------------------------------------------------------
    # PAYMENT LOGIC
    # ---------------------------------------------------------
    def _process_loyalty_payment(self, card, rate):
        for order in self:

            reward = self.env["loyalty.reward"].search([
                ("reward_type", "=", "partial_redeem")
            ], limit=1)

            if not reward:
                raise ValidationError("No Partial Redeem reward configured.")

            if not order.partner_id:
                raise ValidationError("Select customer first.")

            if not order.partner_id.loyalty_partner:
                raise ValidationError("Customer not eligible.")

            if order.amount_total < 0:
                continue

            for payment in order.payment_ids:

                method = payment.payment_method_id
                if not method.is_loyalty_points:
                    continue

                amount = payment.amount
                points_required = round(amount / rate, 2)

                if card.points < points_required:
                    raise ValidationError("Not enough points")

                card.points -= points_required

                self.env["loyalty.history"].create({
                    "card_id": card.id,
                    "issued": 0.0,
                    "used": points_required,
                    "history_type": "part_red",
                    "is_manual_type": True,
                    "description": f"Used {points_required} points",
                    "order_id": order.id,
                })

            order.loyalty_payment_processed = True

    # ---------------------------------------------------------
    # HELPERS (UNCHANGED)
    # ---------------------------------------------------------
    def _get_minimum_amount_for_order(self, order):
        loyalty_program = self.env['loyalty.program'].search([
            ('program_type', '=', 'loyalty'),
            ('active', '=', True)
        ], limit=1)

        if not loyalty_program:
            return 0.0

        rule = self.env['loyalty.rule'].search([
            ('program_id', '=', loyalty_program.id),
            ('minimum_amount', '>', 0)
        ], limit=1)

        return float(rule.minimum_amount) if rule else 0.0

    def _get_total_refunded_amount(self, original_order, exclude_current_order=None):
        total = 0.0

        refunds = self.search([
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('amount_total', '<', 0)
        ])

        for r in refunds:
            if exclude_current_order and r.id == exclude_current_order.id:
                continue

            for line in r.lines:
                if line.qty < 0 and line.refunded_orderline_id:
                    if line.refunded_orderline_id.order_id.id == original_order.id:
                        total += abs(line.price_subtotal_incl)

        return total

    def _get_total_reversed_points(self, original_order, card):
        records = self.env["loyalty.history"].search([
            ("card_id", "=", card.id),
            ("history_type", "=", "refund"),
            ("used", ">", 0),
            ("order_id", "=", original_order.id),
        ])
        return sum(records.mapped("used"))

    # ---------------------------------------------------------
    # RESTORE REWARD
    # ---------------------------------------------------------
    def _restore_reward_points_on_refund(self, card):
        restored = 0.0

        for order in self:

            for line in order.lines:
                if line.qty >= 0:
                    continue

                original = line.refunded_orderline_id
                if not original:
                    continue

                if not getattr(original, "is_reward_line", False):
                    continue

                original_order = original.order_id

                redemption_lines = self.env["loyalty.history"].search([
                    ("card_id", "=", card.id),
                    ("order_id", "=", original_order.id),
                    ("history_type", "in", ("part_red", "redeem", "earn_red")),
                    ("used", ">", 0),
                ])

                points_spent = sum(redemption_lines.mapped("used"))
                if points_spent <= 0:
                    continue

                # -------------------------------------------------
                # FIX: look for reward_refund, not refund.
                # A product-refund row must not block the reward
                # restoration.
                # -------------------------------------------------
                already = self.env["loyalty.history"].search([
                    ("card_id", "=", card.id),
                    ("history_type", "=", "reward_refund"),
                    ("order_id", "=", original_order.id),
                ])

                if already:
                    continue

                restored += points_spent

                self.env["loyalty.history"].create({
                    "card_id": card.id,
                    "issued": points_spent,
                    "used": 0.0,
                    "history_type": "reward_refund",
                    "is_manual_type": True,
                    "description": "Reward restored",
                    "order_id": original_order.id,
                })

        return restored