from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class OrderInquiry(models.Model):
    _name = 'order.inq'
    _order = 'sequence, date_order, id'
    _rec_name = 'name'

    name = fields.Char(default="New", readonly=True, copy=False, tracking=True,string="Inquiry No.")
    description = fields.Char(string="Inquiry Description", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, string='Company')
    contact_person = fields.Char(string="Contact Person", required=True)
    designation = fields.Char(string="Designation")
    user_id = fields.Many2one('res.users', string='Inquiry BY', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('type', '!=', 'private')])
    email = fields.Char(string="Customer Email", related='partner_id.email')
    contact_person_email = fields.Char(string="Contact Person Email")
    contact_person_phone = fields.Char(string="Contact Person Phone")
    state = fields.Selection(
        [('pending', 'Pending'), ('confirm', 'Posted'), ('cancel', 'cancel'), ('reject', 'Rejected')],
        default='pending', string='state')
    deadline_submission = fields.Date(string="Deadline of Submission", required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_ids = fields.Many2many('sale.order', string="Sale Order's")
    multi_order = fields.Boolean('Multi Orders')
    sale_count = fields.Integer(compute="compute_sale_count", store=True)

    date_order = fields.Datetime(string="Inquiry Date", required=True, readonly=False, copy=False, help="Inquiry Date",
                                 default=fields.Datetime.now)
    sequence = fields.Integer(string="Sequence", default=10)

    rejection_reason = fields.Text(string="Rejection Reason")

    @api.depends('sale_order_ids')
    def compute_sale_count(self):
        if self.sale_order_id:
            self.sale_count = len(self.sale_order_ids)
        else:
            self.sale_count = None

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('order.inq.sequence') or "New"
        return super(OrderInquiry, self).create(vals)

    def button_cancel(self):
        if self.state == 'pending':
            self.state = 'cancel'


    def reset_pending(self):
        self.state = 'pending'

    def button_confirm(self, sales_list=None):
        self.state = 'confirm'

    def view_sale_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'domain': [('id', 'in', self.sale_order_ids.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_create_quotation(self):
        self.ensure_one()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_inquiry_id': self.id,
        })

        self.sale_order_id = sale_order.id
        self.sale_order_ids = [(4, sale_order.id)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Created',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
        }

    @api.constrains('deadline_submission', 'date_order')
    def _check_deadline_date(self):
        for rec in self:
            if rec.deadline_submission and rec.date_order:
                min_deadline = rec.date_order.date() + timedelta(days=5)
                if rec.deadline_submission < min_deadline:
                    raise ValidationError(_("Deadline of Submission must be at least 5 days after the Inquiry Date."))

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "order.inq.reject.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_inquiry_id": self.id,
            },
        }


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    order_inquiry_id = fields.Many2one('order.inq', string='Order Inquiry ID')


class RejectReasonWizard(models.TransientModel):
    _name = 'order.inq.reject.reason.wizard'
    _description = 'Reject Reason Wizard'
    inquiry_id = fields.Many2one('order.inq', required=True)
    reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.inquiry_id.write({'state': 'reject', 'rejection_reason': self.reason})
