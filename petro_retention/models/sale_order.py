from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    retention_percent = fields.Float(
        string="Retention (%)",
        digits=(16, 4),
        default=0.0,
        copy=False,
        help="Retention percentage withheld from each invoice (based on invoice base).",
    )

    retention_amount_total = fields.Monetary(
        string="Retention Amount",
        currency_field="currency_id",
        compute="_compute_retention_totals",
        inverse="_inverse_retention_amount_total",
        store=True,
        copy=False,
        help="Total retention to be withheld across all invoices (computed from %). You can edit it; % will be recalculated.",
    )

    retention_withheld_total = fields.Monetary(
        string="Retention Withheld",
        currency_field="currency_id",
        compute="_compute_retention_totals",
        store=False,
        copy=False,
    )

    retention_remaining = fields.Monetary(
        string="Retention Remaining",
        currency_field="currency_id",
        compute="_compute_retention_totals",
        store=False,
        copy=False,
    )

    # -------------------------
    # Helpers
    # -------------------------
    def _get_retention_product(self):
        product_id = int(self.env["ir.config_parameter"].sudo().get_param(
            "petro_retention.retention_product_id", "0"
        ) or 0)
        return self.env["product.product"].browse(product_id).exists()

    def _retention_sale_line(self):
        """One hidden SO line used only as a carrier to create invoice lines (like DP line carrier)."""
        self.ensure_one()
        return self.order_line.filtered(lambda l: getattr(l, "is_retention", False) and not l.display_type)[:1]

    def _ensure_retention_sale_line(self):
        self.ensure_one()
        line = self._retention_sale_line()
        if line:
            return line

        product = self._get_retention_product()
        if not product:
            raise UserError(_("No Retention Product configured. Set it in Settings → Retention."))

        # Create minimal carrier line
        line = self.env["sale.order.line"].create({
            "order_id": self.id,
            "product_id": product.id,
            "name": _("Retention Deduction"),
            "product_uom_qty": 0.0,
            "price_unit": 0.0,
            "discount": 0.0,
            "is_retention": True,
        })
        return line

    def _retention_total_amount(self):
        """Total retention based on amount_untaxed (common in construction)."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        base = currency.round(self.amount_untaxed or 0.0)
        return currency.round(base * (self.retention_percent or 0.0) / 100.0)

    def _retention_withheld_amount(self):
        """Net withheld from posted invoices/refunds linked to the retention carrier line."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        line = self._retention_sale_line()
        if not line:
            return 0.0

        amls = line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type in ("out_invoice", "out_refund")
        )

        # signed subtotal: out_invoice negative line -> negative, out_refund reversal -> positive
        signed_sum = sum((getattr(l, "price_subtotal_signed", l.price_subtotal) or 0.0) for l in amls)
        withheld = currency.round(-signed_sum)  # negative lines => positive withheld
        return max(0.0, withheld)

    def _retention_remaining_amount(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        total = currency.round(self.retention_amount_total or 0.0)
        withheld = currency.round(self._retention_withheld_amount())
        return max(0.0, currency.round(total - withheld))

    # -------------------------
    # Computes / inverse
    # -------------------------
    @api.depends("amount_untaxed", "retention_percent", "order_line.invoice_lines.move_id.state",
                 "order_line.invoice_lines.move_id.move_type", "order_line.invoice_lines.price_subtotal")
    def _compute_retention_totals(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            computed_total = order._retention_total_amount()

            # If retention_amount_total is empty but % is set -> fill it
            # If user already set amount manually -> keep it (inverse will adjust %)
            if (order.retention_percent or 0.0) and currency.is_zero(order.retention_amount_total or 0.0):
                order.retention_amount_total = computed_total

            withheld = order._retention_withheld_amount()
            remaining = order._retention_remaining_amount()

            order.retention_withheld_total = withheld
            order.retention_remaining = remaining

    def _inverse_retention_amount_total(self):
        """If user enters Retention Amount, compute the % from amount_untaxed."""
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            base = currency.round(order.amount_untaxed or 0.0)
            if currency.is_zero(base):
                order.retention_percent = 0.0
                continue
            amt = currency.round(order.retention_amount_total or 0.0)
            order.retention_percent = (amt / base) * 100.0

    # -------------------------
    # Invoice hook (DP-style)
    # -------------------------
    def _get_invoiceable_lines(self, final=False):
        lines = super()._get_invoiceable_lines(final=final)

        # Same pattern as dp_deduct_amounts map you already use :contentReference[oaicite:2]{index=2}
        retention_deduct_amounts = dict(self.env.context.get("retention_deduct_amounts") or {})

        for order in self:
            currency = order.currency_id or order.company_id.currency_id

            # Always keep retention carrier line out of normal invoiceable lines
            ret_line = order._retention_sale_line()
            if ret_line:
                lines = lines.filtered(lambda l: l.id != ret_line.id)

            retention_pct = order.retention_percent or 0.0
            if retention_pct <= 0:
                continue

            remaining = currency.round(order._retention_remaining_amount())
            if currency.is_zero(remaining):
                continue

            # Base lines = invoiceable, real lines (exclude DP + retention)
            base_lines = lines.filtered(
                lambda l: l.order_id == order
                          and not l.display_type
                          and not getattr(l, "is_downpayment", False)
                          and not getattr(l, "is_retention", False)
            )

            # Invoice base (untaxed) like your DP calculation :contentReference[oaicite:3]{index=3}
            invoice_base = 0.0
            for l in base_lines:
                qty = l.qty_to_invoice or 0.0
                if not qty:
                    continue
                unit = l.price_unit or 0.0
                disc = (l.discount or 0.0) / 100.0
                net_unit = unit * (1.0 - disc)
                invoice_base += currency.round(net_unit * qty)

            invoice_base = currency.round(invoice_base)
            if invoice_base <= 0:
                continue

            target = min(remaining, currency.round(invoice_base * retention_pct / 100.0))
            if currency.is_zero(target):
                continue

            retention_deduct_amounts[order.id] = target

            # Add retention carrier line as invoiceable with qty_to_invoice = -1
            ret_line = order._ensure_retention_sale_line()
            lines |= ret_line
            ret_line.qty_to_invoice = -1.0

        return lines.with_context(retention_deduct_amounts=retention_deduct_amounts)
