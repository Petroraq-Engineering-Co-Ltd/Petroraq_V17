from odoo import fields, models
from copy import deepcopy

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import format_amount, html_escape
from odoo.tools.float_utils import float_round, float_compare
from odoo.tools import frozendict
from odoo.fields import Command


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
        """Remaining DP untaxed based on posted moves linked to dp SO line."""
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        amls = dp_line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type == "out_invoice"
        )

        paid = sum(l.price_subtotal for l in amls if (l.price_subtotal or 0.0) > 0.0)
        deducted = sum(abs(l.price_subtotal) for l in amls if (l.price_subtotal or 0.0) < 0.0)

        return max(0.0, paid - deducted)

    def _dp_sale_line(self):
        self.ensure_one()
        return self.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)[:1]

    def _dp_deducted_qty(self):
        """
        How much of DP line (out of 1.0) has already been deducted in REGULAR invoices.
        We count only negative dp quantities from posted customer invoices.
        """
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        deducted = 0.0
        amls = dp_line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type == "out_invoice"
                      and (l.price_subtotal or 0.0) < 0  # only deduction lines
        )
        for aml in amls:
            deducted += abs(aml.quantity or 0.0)

        return max(0.0, min(1.0, float_round(deducted, precision_digits=6)))

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

        for order in self:
            dp_percent = order.dp_percent or 0.0
            if not dp_percent:
                continue

            dp_paid = order._dp_paid_amount()
            if not dp_paid:
                continue  # no posted DP invoice yet

            deducted_qty = order._dp_deducted_qty()
            remaining_qty = max(0.0, 1.0 - deducted_qty)
            if remaining_qty <= 0:
                continue

            # Invoice base (untaxed) for THIS invoice = delivered qty_to_invoice * final_price_unit
            base_lines = lines.filtered(
                lambda l: l.order_id == order and not l.display_type and not l.is_downpayment
            )

            invoice_base = 0.0
            for l in base_lines:
                qty = l.qty_to_invoice if l.qty_to_invoice is not None else 0.0
                # Use your commercial unit price for correct base (since you override invoice line price_unit)
                unit = l.final_price_unit or l.price_unit or 0.0
                invoice_base += qty * unit

            if invoice_base <= 0:
                continue

            remaining_dp_amount = order._dp_remaining_amount()

            vat_factor = 1.15
            target_amount = min(remaining_dp_amount, invoice_base * vat_factor * dp_percent)
            currency = order.currency_id or order.company_id.currency_id
            target_amount = target_amount

            if currency.is_zero(target_amount):
                continue

            fraction = target_amount / dp_paid
            fraction = min(fraction, remaining_qty)

            if fraction <= 0:
                continue

            for dp_so_line in lines.filtered(lambda l: l.order_id == order and l.is_downpayment):
                dp_so_line.qty_to_invoice = -fraction

        return lines
