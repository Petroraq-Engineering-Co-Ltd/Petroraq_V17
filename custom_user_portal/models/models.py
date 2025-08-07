import logging
from odoo import _,models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class PurchaseRequisition(models.Model):
    _name = 'purchase.requisition'
    _description = 'Purchase Requisition'
    _inherit = ['mail.thread' , 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string="PR Number", required=True, copy=False, readonly=True, default='New')
    date_request = fields.Date(string="Date of Request", default=fields.Date.context_today)
    requested_by = fields.Char(string="Requested By")
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    supervisor_partner_id = fields.Char(string="supervisor_partner_id")
    required_date = fields.Date(string="Required Date")
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string="Priority")
    budget_type = fields.Selection([
        ('opex', 'Opex'),
        ('capex', 'Capex')
    ], string="Budget Type")
    budget_details = fields.Char(string="Cost Center Code")
    notes = fields.Text(string="Notes")
    approval = fields.Selection([
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved')
    ], default='pending' , string="Approval")
    comments = fields.Text(string="Comments")
    vendor_id = fields.Many2one('res.partner', string="Preferred Vendor")
    total_excl_vat = fields.Float(string="Total Amount", compute="_compute_totals", store=True, currency_field='currency_id')
    vat_amount = fields.Float(string="VAT (15%)", compute="_compute_totals", store=True, currency_field='currency_id')
    total_incl_vat = fields.Float(string="Total Incl. VAT", compute="_compute_totals", store=True, currency_field='currency_id')
    # currency_id = fields.Many2one('res.currency', string='Currency', required=True,default=lambda self: self.env.ref('base.SAR').id)
    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string="Line Items")

#updating PR code
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == 'New':
                record.name = self.env['ir.sequence'].next_by_code('purchase.requisition') or 'PR0001'
            record._notify_supervisor()
        return records
    
#Checking when PR is approved
    def write(self, vals):
        approval_changed = 'approval' in vals and vals['approval'] == 'approved'
        res = super().write(vals)
        if approval_changed:
            self._notify_procurement_admins()
        return res


    @api.depends('line_ids.total_price')
    def _compute_totals(self):
        for rec in self:
            total = sum(line.total_price for line in rec.line_ids)
            rec.total_excl_vat = total
            rec.vat_amount = total * 0.15
            rec.total_incl_vat = total + rec.vat_amount

# sending activity to specific manager when PR is created
    def _notify_supervisor(self):
        try:
            if self.supervisor_partner_id and self.supervisor_partner_id.isdigit():
                partner_id = int(self.supervisor_partner_id)

                supervisor_user = self.env['res.users'].sudo().search([
                    ('partner_id', '=', partner_id)
                ], limit=1)

                if not supervisor_user:
                    _logger.warning("Supervisor user not found for partner_id=%s", partner_id)
                    return

                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    user_id=supervisor_user.id,
                    summary="Review New PR",
                    note=_("Please review the new Purchase Requisition: <b>%s</b>.") % self.name,
                )

                _logger.info("Activity created for supervisor user_id=%s on PR=%s", supervisor_user.id, self.name)

        except Exception as e:
            _logger.error("Error creating activity for PR=%s: %s", self.name, str(e))

# sending approved PR activity to procurment admin
    def _notify_procurement_admins(self):
        for pr in self:
            try:
                group = self.env.ref('custom_user_portal.procurement_admin')  # 🔁 Replace
                procurement_users = self.env['res.users'].sudo().search([
                    ('groups_id', 'in', group.id)
                ])
                activity_type_id = self.env.ref('mail.mail_activity_data_todo').id

                for user in procurement_users:
                    pr.activity_schedule(
                        activity_type_id=activity_type_id,
                        user_id=user.id,
                        summary="New Approved PR",
                        note=_("A new Purchase Requisition <b>%s</b> has been approved.") % pr.name,
                    )

                _logger.info("Activities scheduled for Procurement Admins on PR=%s", pr.name)

            except Exception as e:
                _logger.error("Error creating procurement admin activities for PR=%s: %s", pr.name, str(e))    

#passing data to rfq form
    def action_create_rfq(self):
        self.ensure_one()

        if not self.vendor_id:
            raise ValidationError("Please select a Vendor before creating RFQ.")

        rfq_lines = []

        # Fetch 15% VAT tax (adjust domain as needed for your DB)
        vat_tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', 15),
            ('amount_type', '=', 'percent')
        ], limit=1)

        for line in self.line_ids:
            product = self.env['product.product'].search([
                ('name', '=', line.unit),
                ('type', 'in', ['product', 'consu', 'service'])
            ], limit=1)

            rfq_lines.append((0, 0, {
                'product_id': product.id if product else False,
                'name': line.description,
                'product_qty': line.quantity,
                'price_unit': line.unit_price,
                'product_uom': product.uom_id.id if product else self.env.ref('uom.product_uom_unit').id,
                'date_planned': fields.Date.context_today(self),
                'taxes_id': [(6, 0, [vat_tax.id])] if vat_tax else [],
            }))

        matched_project = self.env['project.project'].search([
            ('budget_type', '=', self.budget_type),
            ('budget_code', '=', self.budget_details)
        ], limit=1)

        rfq = self.env['purchase.order'].create({
            'partner_id': self.vendor_id.id,
            'order_line': rfq_lines,
            'origin': self.name,
            'notes': self.notes,
            'budget_type': self.budget_type,
            'budget_code': self.budget_details,
            'project_id': matched_project.id if matched_project else False,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Request for Quotation',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': rfq.id,
            'target': 'current',
        }


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'
    _description = 'Purchase Requisition Line'

    requisition_id = fields.Many2one('purchase.requisition', string="Requisition", ondelete="cascade")
    description = fields.Char(string="Item Description")
    type = fields.Char(string="Type")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    unit_price = fields.Float(string="Unit Price")
    total_price = fields.Float(string="Total", compute="_compute_total", store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.unit_price


class PurchaseQuotation(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one('project.project', string="Project")   
    budget_type = fields.Selection([
        ('opex', 'Opex'),
        ('capex', 'Capex')
    ], string="Budget Type")

    budget_code = fields.Char(string="Budget Code")
    project_id = fields.Many2one('project.project', string='Project')
