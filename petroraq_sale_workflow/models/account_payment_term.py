from odoo import fields, models

from odoo.tools.float_utils import float_round, float_compare


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    petroraq_selectable = fields.Boolean(
        string="Selectable for Petroraq Sales",
        default=False,
    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _dp_paid_amount(self):
        """Total DP untaxed that was posted (positive DP invoices only)."""
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        amls = dp_line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type == "out_invoice"
                      and (l.price_subtotal or 0.0) > 0.0
        )
        return sum(amls.mapped("price_subtotal")) or 0.0

    def _dp_remaining_amount(self):
        """Remaining DP = paid - deducted (all posted, untaxed)."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        paid = currency.round(self._dp_paid_amount())
        deducted = currency.round(self._dp_deducted_amount())
        return max(0.0, currency.round(paid - deducted))

    def _dp_sale_line(self):
        self.ensure_one()
        return self.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)[:1]

    def _dp_deducted_amount(self):
        """Total DP deducted (untaxed) from posted regular invoices (negative dp lines)."""
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        amls = dp_line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type == "out_invoice"
                      and (l.price_subtotal or 0.0) < 0.0
        )
        return sum(abs(l.price_subtotal) for l in amls) or 0.0

    def _is_fully_delivered(self):
        """Final invoice if all stockable/consu lines are fully delivered."""
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda l: not l.display_type and not l.is_downpayment and l.product_id
        ).filtered(lambda l: l.product_id.type in ("product", "consu"))

        if not lines:
            return False

        for l in lines:
            if float_compare(
                    l.qty_delivered, l.product_uom_qty,
                    precision_rounding=l.product_uom.rounding
            ) < 0:
                return False
        return True

    def _get_invoiceable_lines(self, final=False):
        lines = super()._get_invoiceable_lines(final=final)

        dp_deduct_amounts = dict(self.env.context.get("dp_deduct_amounts") or {})

        for order in self:
            dp_percent = order.dp_percent or 0.0
            if not dp_percent:
                continue

            currency = order.currency_id or order.company_id.currency_id
            remaining_dp_amount = currency.round(order._dp_remaining_amount())
            if currency.is_zero(remaining_dp_amount):
                continue

            # compute invoice_base from invoiceable non-dp lines (as we discussed)
            base_lines = lines.filtered(
                lambda l: l.order_id == order and not l.display_type and not l.is_downpayment
            )

            invoice_base = 0.0
            for l in base_lines:
                qty = l.qty_to_invoice or 0.0
                unit_r = currency.round(l.final_price_unit or l.price_unit or 0.0)
                invoice_base += currency.round(unit_r * qty)

            invoice_base = currency.round(invoice_base)
            if invoice_base <= 0:
                continue

            target_amount = min(remaining_dp_amount, currency.round(invoice_base * dp_percent))
            if currency.is_zero(target_amount):
                continue

            dp_deduct_amounts[order.id] = target_amount

            # ✅ Force include the DP SO line even if Odoo excluded it
            dp_so_line = order._dp_sale_line()
            if dp_so_line:
                lines |= dp_so_line
                dp_so_line.qty_to_invoice = -1.0  # keep amount in price_unit later

        return lines.with_context(dp_deduct_amounts=dp_deduct_amounts)
