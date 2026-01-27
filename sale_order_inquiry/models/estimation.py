from odoo import fields, models


class PetroraqEstimation(models.Model):
    _inherit = "petroraq.estimation"

    order_inquiry_id = fields.Many2one("order.inq", string="Inquiry", readonly=True)