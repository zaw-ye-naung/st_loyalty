from odoo import models, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    def write(self, vals):
        """
        Track partner changes and state changes to update membership profiles
        """
        # Track which partners are affected by this write
        affected_partners = set()

        # If partner_id is being changed, get old and new partners
        if 'partner_id' in vals:
            for order in self:
                if order.partner_id:
                    affected_partners.add(order.partner_id.id)
            if vals.get('partner_id'):
                affected_partners.add(vals['partner_id'])

        # If state is being changed, track affected orders
        if 'state' in vals:
            for order in self:
                if order.partner_id:
                    affected_partners.add(order.partner_id.id)

        result = super().write(vals)

        # Update membership profiles for affected partners
        if affected_partners:
            profiles = self.env['membership.profile'].search([
                ('partner_id', 'in', list(affected_partners))
            ])
            profiles._compute_totals()
            profiles._compute_tier_id()

        return result

    def unlink(self):
        """
        Update membership profiles when POS orders are deleted
        """
        affected_partners = set()
        for order in self:
            if order.partner_id:
                affected_partners.add(order.partner_id.id)

        result = super().unlink()

        # Update membership profiles for affected partners
        if affected_partners:
            profiles = self.env['membership.profile'].search([
                ('partner_id', 'in', list(affected_partners))
            ])
            profiles._compute_totals()
            profiles._compute_tier_id()

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Track new POS orders to update membership profiles
        """
        records = super().create(vals_list)

        # Update membership profiles for partners in new orders
        affected_partners = set()
        for record in records:
            if record.partner_id:
                affected_partners.add(record.partner_id.id)

        if affected_partners:
            profiles = self.env['membership.profile'].search([
                ('partner_id', 'in', list(affected_partners))
            ])
            profiles._compute_totals()
            profiles._compute_tier_id()

        return records