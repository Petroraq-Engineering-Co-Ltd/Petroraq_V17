from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_mgr_approval_min_amount = fields.Monetary(related="company_id.sale_mgr_approval_min_amount", readonly=False)
    sale_md_approval_min_amount = fields.Monetary(related="company_id.sale_md_approval_min_amount", readonly=False)
    sale_md_user_id = fields.Many2one(related="company_id.sale_md_user_id", readonly=False)

