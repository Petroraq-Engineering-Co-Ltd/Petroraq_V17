from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import re
from odoo.exceptions import UserError


class OrderInquiry(models.Model):
    _name = 'order.inq'
    _order = 'sequence, date_order, id'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default="New", readonly=True, copy=False, tracking=True, string="Inquiry No")
    description = fields.Char(string="Inquiry Description", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, string='Company')
    contact_person = fields.Char(string="Contact Person", required=True)
    designation = fields.Char(string="Designation")
    user_id = fields.Many2one('res.users', string='Inquiry By',
                              domain=lambda self: self._get_salesperson_domain(), )
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('is_company', '=', 'True')])
    email = fields.Char(string="Customer Email", related='partner_id.email')
    contact_person_email = fields.Char(string="Contact Person Email", required=True)
    contact_person_phone = fields.Char(string="Contact Person Phone", required=True)
    state = fields.Selection(
        [('pending', 'Pending'), ('confirm', 'Submitted'), ('accept', 'Accepted'), ('cancel', 'Cancelled'),
         ('reject', 'Rejected'),
         ('expire', 'Expired')],
        default='pending', string='State', tracking=True)
    deadline_submission = fields.Date(string="Deadline", required=True, tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_ids = fields.Many2many('sale.order', string="Sale Order's")
    multi_order = fields.Boolean('Multi Orders')
    sale_count = fields.Integer(compute="compute_sale_count", store=True)

    date_order = fields.Datetime(string="Inquiry Date", required=True, readonly=False, copy=False, help="Inquiry Date",
                                 default=fields.Datetime.now)
    sequence = fields.Integer(string="Sequence", default=10)

    rejection_reason = fields.Text(string="Rejection Reason", tracking=True)
    inquiry_type = fields.Selection([('construction', 'Project'), ('trading', 'Trading')], string="Inquiry Type",
                                    default="construction", required=True)
    required_file = fields.Binary(string="Required Attachment", attachment=False)
    required_file_name = fields.Char(string="Filename")

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    quotation_main_id = fields.Many2one(
        "sale.order",
        string="Main Quotation",
        compute="_compute_quotation_main",
        store=True,
        readonly=True,
    )

    quotation_state = fields.Selection(
        related="quotation_main_id.state",
        string="Quotation Status",
        store=True,
        readonly=True,
    )

    quotation_approval_state = fields.Selection(
        related="quotation_main_id.approval_state",
        string="Quotation Approval Status",
        store=True,
        readonly=True,
    )

    quotation_amount_total = fields.Monetary(
        related="quotation_main_id.profit_grand_total",
        string="Quotation Total",
        currency_field="currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("sale_order_id", "sale_order_ids")
    def _compute_quotation_main(self):
        for rec in self:
            if rec.sale_order_id:
                rec.quotation_main_id = rec.sale_order_id
            elif rec.sale_order_ids:
                rec.quotation_main_id = rec.sale_order_ids.sorted("id")[-1]
            else:
                rec.quotation_main_id = False

    def _inq_default_construction_sections(self):
        """Return section titles to create on quotation for construction inquiries."""
        return ["Material:", "Equipment/Tools", "Third Party Services", "Labor"]

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'sale_order_id': False,
            'sale_order_ids': [(6, 0, [])],
            'state': 'pending',
            'name': 'New',
        })
        return super().copy(default)

    def _get_salesperson_domain(self):
        return [
            ('groups_id', 'in', (
                    self.env.ref('sales_team.group_sale_salesman').ids +
                    self.env.ref('sales_team.group_sale_manager').ids
            ))
        ]

    @api.model
    def _cron_expire_inquiries_without_quotation(self):
        today = fields.Date.today()

        inquiries = self.search([
            ('state', 'in', ['accept', 'confirm']),
            ('deadline_submission', '<', today),
            ('sale_order_ids', '=', False),
        ])

        for inquiry in inquiries:
            inquiry.write({
                'state': 'expire',
            })

    @api.constrains('contact_person_email', 'contact_person_phone')
    def _check_email_and_phone(self):
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        phone_regex = r"^\+?[0-9\s\-]{7,15}$"

        for rec in self:
            if rec.contact_person_email:
                if not re.match(email_regex, rec.contact_person_email):
                    raise ValidationError(
                        _("Invalid email format. Example: name@example.com")
                    )

            if rec.contact_person_phone:
                if not re.match(phone_regex, rec.contact_person_phone):
                    raise ValidationError(
                        _("Invalid phone number. Use digits only, minimum 9 digits, optionally starting with +")
                    )

    @api.constrains('contact_person')
    def _check_contact_person_chars(self):
        name_regex = r'^[A-Za-z\s]+$'
        for rec in self:
            if rec.contact_person and not re.match(name_regex, rec.contact_person):
                raise ValidationError(
                    _("Contact Person name must contain letters only (no numbers or special characters).")
                )

    @api.constrains('deadline_submission', 'date_order')
    def _check_deadline_date(self):
        for rec in self:
            if rec.deadline_submission and rec.date_order:
                inquiry_date = rec.date_order.date()
                max_deadline = inquiry_date + timedelta(days=30)

                if rec.deadline_submission < inquiry_date:
                    raise ValidationError(
                        _("Deadline of Submission cannot be before the Inquiry Date.")
                    )

                if rec.deadline_submission > max_deadline:
                    raise ValidationError(
                        _("Deadline of Submission cannot exceed 30 days from the Inquiry Date.")
                    )

    @api.depends('sale_order_ids')
    def compute_sale_count(self):
        if self.sale_order_id:
            self.sale_count = len(self.sale_order_ids)
        else:
            self.sale_count = None

    def action_accept(self):
        self.state = 'accept'

    @api.model
    def create(self, vals):
        # sequence
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('order.inq.sequence') or "New"

        # require file at create-time
        if not vals.get("required_file"):
            raise UserError(_("You must upload the required attachment before creating the inquiry."))

        file_content = vals.pop("required_file")
        file_name = vals.pop("required_file_name", "Inquiry Attachment")

        rec = super(OrderInquiry, self).create(vals)

        self.env["ir.attachment"].create({
            "name": file_name,
            "datas": file_content,
            "res_model": "order.inq",
            "res_id": rec.id,
            "type": "binary",
            "mimetype": False,
        })

        return rec

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
            'inquiry_type': self.inquiry_type,
        })

        self.sale_order_id = sale_order.id
        self.sale_order_ids = [(4, sale_order.id)]

        if self.inquiry_type == 'construction':
            SaleOrderLine = self.env['sale.order.line']
            seq = 10
            for title in self._inq_default_construction_sections():
                SaleOrderLine.create({
                    'order_id': sale_order.id,
                    'display_type': 'line_section',
                    'name': title,
                    'sequence': seq,
                    'is_locked_section': True
                })
                seq += 10

        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Created',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
        }

    def action_extend_deadline(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'order.inq.extend.deadline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_inquiry_id': self.id,
            }
        }

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
    inquiry_type = fields.Selection(related='order_inquiry_id.inquiry_type', )
    inquiry_contact_person = fields.Char(related='order_inquiry_id.contact_person')
    inquiry_contact_person_phone = fields.Char(related='order_inquiry_id.contact_person_phone')
    inquiry_contact_person_email = fields.Char(related='order_inquiry_id.contact_person_email')
    inquiry_contact_person_designation = fields.Char(related='order_inquiry_id.designation')

    def _so_renumber_lines_with_gaps(self):
        self.ensure_one()
        seq = 10
        for l in self.order_line.sorted("sequence"):
            l.sequence = seq
            seq += 10

    def _so_next_line_after(self, line):
        self.ensure_one()
        lines = self.order_line.sorted("sequence")
        return lines.filtered(lambda l: l.sequence > line.sequence)[:1]

    def action_add_line_under_section(self, section_line_id, mode="product"):
        """
        mode: 'product' | 'section' | 'note'
        """
        self.ensure_one()

        section = self.env["sale.order.line"].browse(section_line_id).exists()
        if not section or section.order_id.id != self.id:
            raise UserError(_("Invalid section line."))
        if section.display_type != "line_section":
            raise UserError(_("Target is not a section."))

        next_line = self._so_next_line_after(section)

        if next_line and (next_line.sequence - section.sequence) > 1:
            new_seq = section.sequence + 1
        else:
            self._so_renumber_lines_with_gaps()
            new_seq = section.sequence + 10

        vals = {"order_id": self.id, "sequence": new_seq}

        if mode == "section":
            vals.update({"display_type": "line_section", "name": _("New Section")})
        elif mode == "note":
            vals.update({"display_type": "line_note", "name": _("New Note")})
        # else product: keep empty -> user selects product

        line = self.env["sale.order.line"].create(vals)
        return line.id


class RejectReasonWizard(models.TransientModel):
    _name = 'order.inq.reject.reason.wizard'
    _description = 'Reject Reason Wizard'
    inquiry_id = fields.Many2one('order.inq', required=True)
    reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.inquiry_id.write({'state': 'reject', 'rejection_reason': self.reason})


class OrderInquiryExtendDeadlineWizard(models.TransientModel):
    _name = 'order.inq.extend.deadline.wizard'
    _description = 'Extend Inquiry Deadline'

    inquiry_id = fields.Many2one('order.inq', required=True, readonly=True)
    current_deadline = fields.Date(string="Current Deadline", readonly=True)
    new_deadline = fields.Date(string="New Deadline", required=True)

    def action_confirm_extend(self):
        self.inquiry_id.write({
            'deadline_submission': self.new_deadline,
            'state': 'confirm',
        })


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_locked_section = fields.Boolean(default=False)

    def unlink(self):
        for l in self:
            if l.display_type == "line_section" and l.is_locked_section:
                raise UserError(_("You cannot delete default sections."))
        return super().unlink()

    # def write(self, vals):
    #     for l in self:
    #         if l.display_type == "line_section" and l.is_locked_section:
    #             raise UserError(_("You cannot modify default sections"))
    #     return super().write(vals)
