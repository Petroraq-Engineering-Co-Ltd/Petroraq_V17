from odoo import models, fields, api
from odoo.exceptions import ValidationError

class GrnSes(models.Model):
    _name = "grn.ses"
    _description = "GRN / SES"

    name = fields.Char(string="Reference", required=True)
    partner_ref = fields.Char(string="Vendor Reference")
    date_order = fields.Date(string="Order Date")
    date_planned = fields.Date(string="Planned Date")
    project = fields.Char(string="Project")
    line_ids = fields.One2many(
        "grn.ses.line", "order_id", string="GRN/SES Lines"
    )

class GrnSesLine(models.Model):
    _name = "grn.ses.line"
    _description = "GRN/SES Line"

    order_id = fields.Many2one(
        "grn.ses",
        string="GRN/SES",
        ondelete="cascade",
        required=True
    )
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    price_unit = fields.Float(string="Unit Price")
    remarks = fields.Char(string="Remarks")
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

class GrnSesWizard(models.TransientModel):
    _name = "grn.ses.wizard"
    _description = "Wizard for GRN/SES Creation"

    remarks = fields.Text(string="Remarks")

    def action_create_grn_ses(self):
        active_id = self.env.context.get('active_id')
        order = self.env['purchase.order'].browse(active_id)

        # 🔎 Check if GRN/SES already exists for this PO
        existing_grn = self.env['grn.ses'].search([('name', '=', f"GRN/SES for {order.name}")], limit=1)
        if existing_grn:
            # Just close wizard, no duplicate creation
            raise ValidationError(f"A GRN/SES already exists for {order.name}. Duplicate creation is not allowed.")

        # 🚀 Create new GRN/SES if not found
        grn_ses = self.env['grn.ses'].create({
            'name': f"GRN/SES for {order.name}",
            'partner_ref': order.partner_ref,
            'date_order': order.date_order,
            'date_planned': order.date_planned,
            'project': order.project_id.name if order.project_id else False,
        })

        # Copy lines
        line_vals = []
        for line in order.custom_line_ids:
            line_vals.append((0, 0, {
                'name': line.name,
                'quantity': line.quantity,
                'unit': line.unit,
                'price_unit': line.price_unit,
                'subtotal': line.subtotal,
                'remarks': self.remarks,   # remarks from popup
            }))
        
        if line_vals:
            grn_ses.write({'line_ids': line_vals})

        return {'type': 'ir.actions.act_window_close'}