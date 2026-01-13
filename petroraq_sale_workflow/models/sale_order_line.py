from odoo import api, fields, models, _
from odoo.tools import format_amount, html_escape


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    section_subtotal_amount = fields.Monetary(
        string="Section Subtotal",
        compute="_compute_section_subtotal_amount",
        store=False,
        currency_field="currency_id",
        help="Subtotal of the products within this section."
    )
    section_subtotal_display = fields.Html(
        string="Section Subtotal Display",
        compute="_compute_section_subtotal_amount",
        sanitize=False,
        help="Formatted subtotal snippet for section headers."
    )

    # IMPORTANT: not stored, and use Monetary
    final_price_unit = fields.Monetary(
        string="Final Unit Price",
        compute="_compute_final_price_unit",
        store=False,
        currency_field="currency_id",
    )

    @api.depends(
        "price_unit",
        "order_id.overhead_percent",
        "order_id.risk_percent",
        "order_id.profit_percent",
        "currency_id",
        "display_type",
        "is_downpayment",
    )
    def _compute_final_price_unit(self):
        for line in self:
            if line.display_type or getattr(line, "is_downpayment", False) or not line.order_id:
                line.final_price_unit = line.price_unit or 0.0
                continue

            order = line.order_id
            currency = line.currency_id or order.currency_id or order.company_id.currency_id

            breakdown = order._costing_line_breakdown(
                base_unit=line.price_unit or 0.0,
                qty=1.0,
                currency=currency,
            )
            line.final_price_unit = breakdown["final_u"]

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        # Normal product lines: force invoice to use the same costing unit
        if not self.display_type and not getattr(self, "is_downpayment", False):
            order = self.order_id
            currency = self.currency_id or order.currency_id or order.company_id.currency_id
            breakdown = order._costing_line_breakdown(
                base_unit=self.price_unit or 0.0,
                qty=1.0,
                currency=currency,
            )
            vals["price_unit"] = breakdown["final_u"]
            return vals

        # Downpayment deduction line: force amount-based deduction
        if getattr(self, "is_downpayment", False) and not self.display_type:
            qty = vals.get("quantity") or 0.0
            if qty < 0:  # deduction line
                amount_map = self.env.context.get("dp_deduct_amounts") or {}
                target_amount = amount_map.get(self.order_id.id)

                if target_amount:
                    vals["quantity"] = -1.0
                    vals["price_unit"] = target_amount
                    vals["discount"] = 0.0

        return vals

    # =========================
    # Section subtotal chips
    # =========================
    @api.depends(
        "display_type",
        "sequence",
        "order_id.order_line.display_type",
        "order_id.order_line.sequence",
        "order_id.order_line.price_unit",
        "order_id.order_line.product_uom_qty",
        "order_id.order_line.is_downpayment",
        "order_id.overhead_percent",
        "order_id.risk_percent",
        "order_id.profit_percent",
        "currency_id",
    )
    def _compute_section_subtotal_amount(self):
        label = _("Sub Total")

        for line in self:
            line.section_subtotal_amount = 0.0
            line.section_subtotal_display = False

        for order in self.mapped("order_id"):
            currency = order.currency_id or order.company_id.currency_id

            subtotal = 0.0
            current_section = None

            ordered_lines = order.order_line.sorted(key=lambda l: (l.sequence or 0, l.id or 0))
            for line in ordered_lines:
                if line.display_type == "line_section":
                    if current_section:
                        current_section._set_section_subtotal_values(subtotal, label)
                    current_section = line
                    subtotal = 0.0
                    line.section_subtotal_amount = 0.0
                    line.section_subtotal_display = False
                    continue

                if line.display_type or getattr(line, "is_downpayment", False):
                    continue

                # Costing subtotal (same as PDF)
                breakdown = order._costing_line_breakdown(
                    base_unit=line.price_unit or 0.0,
                    qty=line.product_uom_qty or 0.0,
                    currency=currency,
                )
                subtotal += breakdown["total_line"]

            if current_section:
                current_section._set_section_subtotal_values(subtotal, label)

    def _set_section_subtotal_values(self, amount, label):
        self.ensure_one()
        currency = self.order_id.currency_id or self.order_id.company_id.currency_id
        amount_display = format_amount(self.env, amount or 0.0, currency) if currency else f"{(amount or 0.0):.2f}"

        self.section_subtotal_amount = amount
        self.section_subtotal_display = (
            f"<span class='o_section_subtotal_chip_label'>{html_escape(label)}</span>"
            f"<span class='o_section_subtotal_chip_value'>{html_escape(amount_display)}</span>"
        )
