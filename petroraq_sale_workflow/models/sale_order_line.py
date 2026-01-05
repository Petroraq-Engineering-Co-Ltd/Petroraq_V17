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
    final_price_unit = fields.Float(
        string="Final Unit Price",
        compute="_compute_final_price_unit",
        store=True
    )

    @api.depends('price_unit', 'order_id.overhead_percent', 'order_id.risk_percent', 'order_id.profit_percent')
    def _compute_final_price_unit(self):
        for line in self:
            # skip sections/notes + down payments
            if line.display_type or getattr(line, "is_downpayment", False):
                line.final_price_unit = line.price_unit
                continue

            base = line.price_unit or 0.0
            overhead = base * (line.order_id.overhead_percent / 100.0)
            risk = base * (line.order_id.risk_percent / 100.0)
            unit_or = base + overhead + risk
            profit = unit_or * (line.order_id.profit_percent / 100.0)
            line.final_price_unit = unit_or + profit

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        if not self.display_type and not self.is_downpayment:
            vals["price_unit"] = self.final_price_unit

        return vals

    @api.depends(
        "display_type",
        "price_subtotal",
        "sequence",
        "order_id.order_line.price_subtotal",
        "order_id.order_line.display_type",
        "order_id.order_line.sequence",
    )
    def _compute_section_subtotal_amount(self):
        label = _("Sub Total")
        for line in self:
            line.section_subtotal_amount = 0.0
            line.section_subtotal_display = False

        for order in self.mapped("order_id"):
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
                elif line.display_type:
                    continue
                else:
                    subtotal += line.price_subtotal
            if current_section:
                current_section._set_section_subtotal_values(subtotal, label)

    def _set_section_subtotal_values(self, amount, label):
        self.ensure_one()
        currency = self.order_id.currency_id or self.order_id.company_id.currency_id
        if currency:
            amount_display = format_amount(self.env, amount, currency)
        else:
            amount_display = f"{amount:.2f}"
        self.section_subtotal_amount = amount
        self.section_subtotal_display = (
            f"<span class='o_section_subtotal_chip_label'>{html_escape(label)}</span>"
            f"<span class='o_section_subtotal_chip_value'>{html_escape(amount_display)}</span>"
        )
