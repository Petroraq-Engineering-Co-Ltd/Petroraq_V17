from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def action_add_product_after_section(self, order_id, section_line_id, product_id):
        order = self.browse(order_id).exists()
        section = self.env["sale.order.line"].browse(section_line_id).exists()
        if not order or not section or section.order_id.id != order.id:
            return False

        next_line = self.env["sale.order.line"].search(
            [("order_id", "=", order.id), ("sequence", ">", section.sequence)],
            order="sequence asc",
            limit=1
        )
        seq = (section.sequence + next_line.sequence) / 2.0 if next_line else (section.sequence + 1.0)

        # Just create: Odoo 17 will precompute name/uom/taxes/price/discount, etc.
        self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product_id,
            "product_uom_qty": 1.0,
            "sequence": seq,
        })
        return True
