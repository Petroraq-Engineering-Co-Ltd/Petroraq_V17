from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleInquiry(models.Model):
    _name = "sale.inquiry"
    _description = "Sales Inquiry"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char("Inquiry Subject", required=True, tracking=True, default=lambda s: _("New Inquiry"))
    partner_id = fields.Many2one("res.partner", string="Customer", required=True, tracking=True)
    user_id = fields.Many2one("res.users", string="Salesperson", default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    expected_revenue = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)
    description = fields.Text("Notes")
    state = fields.Selection([
        ("new", "New"),
        ("quoted", "Quotation Created"),
        ("won", "Won"),
        ("lost", "Lost"),
    ], default="new", tracking=True)
    sale_order_id = fields.Many2one("sale.order", string="Quotation")

    def action_create_quotation(self):
        self.ensure_one()
        if self.sale_order_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "sale.order",
                "view_mode": "form",
                "res_id": self.sale_order_id.id,
            }
        order_vals = {
            "partner_id": self.partner_id.id,
            "origin": f"Inquiry:{self.name}",
            "user_id": self.user_id.id,
            "company_id": self.company_id.id,
            "approval_state": "draft",
        }
        order = self.env["sale.order"].create(order_vals)
        self.sale_order_id = order.id
        self.state = "quoted"
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": order.id,
        }

