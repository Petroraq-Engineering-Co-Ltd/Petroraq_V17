from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class PurchaseQuotation(models.Model):
    _name = "purchase.quotation"
    _description = "Purchase Quotation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    # Basic Info
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    rfq_origin = fields.Char(string="RFQ Origin")
    vendor_ref = fields.Char(string="Vendor Reference")
    notes = fields.Text(string="Notes")
    order_deadline = fields.Datetime(string="Deadline")
    expected_arrival = fields.Datetime(string="Expected Arrival")

    # Supplier Info
    supplier_name = fields.Char(string="Supplier Name")
    contact_person = fields.Char(string="Contact Person")
    company_address = fields.Char(string="Company Address")
    phone_number = fields.Char(string="Phone Number")
    email_address = fields.Char(string="Email Address")
    supplier_id = fields.Char(string="Supplier ID")
    quotation_ref = fields.Char(string="Quotation Reference")

    # Payment Terms
    terms_net = fields.Boolean("Net")
    terms_30days = fields.Boolean("30 Days")
    terms_advance = fields.Boolean("Advance %")
    terms_advance_specify = fields.Char("Specify Advance Terms")
    terms_delivery = fields.Boolean("On Delivery")
    terms_other = fields.Boolean("Other")
    terms_others_specify = fields.Char("Specify Other Terms")

    # Production / Material Availability
    ex_stock = fields.Boolean("Ex-Stock")
    required_days = fields.Boolean("Production Required")
    production_days = fields.Char("Production Days Needed")

    # Delivery Terms
    ex_work = fields.Boolean("Ex-Works")
    delivery_site = fields.Boolean("Site Delivery")

    # Delivery Date Expected
    delivery_date = fields.Date("Expected Delivery Date")

    # Delivery Method
    delivery_courier = fields.Boolean("Courier")
    delivery_pickup = fields.Boolean("Pickup")
    delivery_freight = fields.Boolean("Freight")
    delivery_others = fields.Boolean("Other")
    delivery_others_specify = fields.Char("Specify Other Delivery")

    # Partial Order Acceptance
    partial_yes = fields.Boolean("Partial Order Acceptable")
    partial_no = fields.Boolean("Partial Order Not Acceptable")

    # total
    total_excl_vat = fields.Float(
        string="Total Amount", compute="_compute_totals", store=True
    )
    vat_amount = fields.Float(
        string="VAT Amount @ 15%", compute="_compute_totals", store=True
    )
    total_incl_vat = fields.Float(
        string="Total Amount Including VAT", compute="_compute_totals", store=True
    )
    is_best = fields.Boolean(
        string="Best Quotation", compute="_compute_is_best", store=True
    )
    is_best_badge = fields.Char(
        string="Best Quotation", compute="_compute_is_best_badge", store=False
    )

    # budget
    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type"
    )
    budget_code = fields.Char(string="Budget Code")
    project_id = fields.Many2one("project.project", string="Project")
    project_budget_allowance = fields.Float(
        string="Project Budget Allowance",
        related="project_id.budget_allowance",
        readonly=True,
        store=False,
    )
    budget_left = fields.Float(
        string="Budget Left", related="project_id.budget_left", store=False
    )

    # Lines
    line_ids = fields.One2many(
        "purchase.quotation.line", "quotation_id", string="Quotation Lines"
    )

    @api.depends("line_ids.unit_price", "line_ids.quantity")
    def _compute_totals(self):
        for record in self:
            total_excl = sum(
                line.unit_price * line.quantity for line in record.line_ids
            )
            record.total_excl_vat = total_excl
            record.vat_amount = total_excl * 0.15
            record.total_incl_vat = total_excl + record.vat_amount

    @api.depends("rfq_origin", "total_incl_vat")
    def _compute_is_best(self):
        # Group records by rfq_origin
        grouped = {}
        for rec in self:
            if rec.rfq_origin and rec.total_incl_vat:
                grouped.setdefault(rec.rfq_origin, []).append(rec)

        for group in grouped.values():
            # Get minimum total_incl_vat in group
            min_amount = min(rec.total_incl_vat for rec in group)
            for rec in group:
                rec.is_best = rec.total_incl_vat == min_amount

    @api.depends("is_best")
    def _compute_is_best_badge(self):
        for rec in self:
            rec.is_best_badge = "Best" if rec.is_best else ""

    def action_create_purchase_order(self):
        self.ensure_one()

        if self.budget_left < self.total_incl_vat:
            raise UserError(
                "Insufficient budget. You cannot proceed with Purchase Order creation."
            )

        # Get 15% VAT tax
        vat_tax = self.env["account.tax"].search(
            [("amount", "=", 15), ("type_tax_use", "=", "purchase")], limit=1
        )

        # Create PO
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor_id.id,
                "partner_ref": self.vendor_ref,
                "date_order": self.order_deadline or fields.Datetime.now(),
                "origin": self.rfq_origin,
                "project_id": self.project_id.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_qty": line.quantity,
                            "price_unit": line.unit_price,
                            "date_planned": self.expected_arrival
                            or fields.Datetime.now(),
                            "taxes_id": [(6, 0, [vat_tax.id])] if vat_tax else False,
                        },
                    )
                    for line in self.line_ids
                ],
            }
        )

        purchase_order.button_confirm()

        # 💡 Determine group based on amount
        amount = self.total_incl_vat
        group_xml_id = None

        if amount <= 10000:
            group_xml_id = "custom_user_portal.procurement_admin"
        elif amount <= 100000:
            group_xml_id = "custom_user_portal.project_engineer"
        elif amount <= 500000:
            group_xml_id = "custom_user_portal.project_manager"
        else:
            group_xml_id = "custom_user_portal.operations_director"

        # 💡 Create activity for all users in that group
        if group_xml_id:
            group = self.env.ref(group_xml_id)
            for user in group.users:
                self.env["mail.activity"].create(
                    {
                        "res_model_id": self.env["ir.model"]._get("purchase.order").id,
                        "res_id": purchase_order.id,
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "summary": "Review Purchase Order",
                        "user_id": user.id,
                        "note": f"Please review the Purchase Order for {self.rfq_origin}.",
                        "date_deadline": fields.Date.today(),
                    }
                )

        return {
            "type": "ir.actions.act_window",
            "name": "Purchase Order",
            "res_model": "purchase.order",
            "res_id": purchase_order.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PurchaseQuotation, self).create(vals_list)

        # Define group references
        procurement_admin_group = self.env.ref(
            "custom_user_portal.procurement_admin", raise_if_not_found=False
        )
        project_engineer_group = self.env.ref(
            "custom_user_portal.project_engineer", raise_if_not_found=False
        )
        project_manager_group = self.env.ref(
            "custom_user_portal.project_manager", raise_if_not_found=False
        )
        operations_director_group = self.env.ref(
            "custom_user_portal.operations_director", raise_if_not_found=False
        )

        for record in records:
            target_group = None

            if record.total_incl_vat <= 10000:
                target_group = procurement_admin_group
            elif 10000 < record.total_incl_vat <= 100000:
                target_group = project_engineer_group
            elif 100000 < record.total_incl_vat <= 500000:
                target_group = project_manager_group
            elif record.total_incl_vat > 500000:
                target_group = operations_director_group

            if target_group:
                for user in target_group.users:
                    record.activity_schedule(
                        "mail.mail_activity_data_todo",
                        summary="New Purchase Quotation Created",
                        note=f"A new purchase quotation (ID: {record.id}) has been created with a total amount of {record.total_incl_vat:.2f}.",
                        user_id=user.id,
                    )

        return records


# For budget
# @api.depends('status', 'total_incl_vat', 'project_budget_allowance')
# def _compute_budget_left(self):
#     for record in self:
#         if record.status == 'approved':
#             record.budget_left = record.project_budget_allowance - record.total_incl_vat
#         else:
#             record.budget_left = record.project_budget_allowance


class PurchaseQuotationLine(models.Model):
    _name = "purchase.quotation.line"
    _description = "Purchase Quotation Line"

    quotation_id = fields.Many2one("purchase.quotation", string="Quotation")
    product_id = fields.Many2one("product.product", string="Product")
    quantity = fields.Float(string="Quantity")
    unit_price = fields.Float(string="Unit Price")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    description = fields.Char()
    name = fields.Char()
    display_name_ui = fields.Char(
        string="Product", compute="_compute_display_name_ui", store=False
    )

    @api.depends("product_id", "name")
    def _compute_display_name_ui(self):
        for line in self:
            line.display_name_ui = (
                line.product_id.name if line.product_id else line.name
            )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    status = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        string="Status",
        default="pending",
    )

    def write(self, vals):
        for record in self:
            status = vals.get("status")
            if status in ["approved", "rejected"]:
                _logger.info("STATUS CHANGED TO '%s' for PO %s", status, record.name)
                _logger.info(
                    "Origin during status change: %s", record.origin or "No origin set"
                )

                if record.origin:
                    prev_po = self.search([("name", "=", record.origin)], limit=1)
                    if prev_po:
                        pr_origin = prev_po.origin
                        _logger.info(
                            "Origin of origin (from %s): %s",
                            record.origin,
                            pr_origin or "No origin set",
                        )

                        if pr_origin:
                            pr = self.env["purchase.requisition"].search(
                                [("name", "=", pr_origin)], limit=1
                            )
                            if pr:
                                supervisor_partner_id = pr.supervisor_partner_id
                                try:
                                    supervisor_id_int = int(supervisor_partner_id)
                                    _logger.info(
                                        "Supervisor partner ID (int): %s",
                                        supervisor_id_int,
                                    )

                                    # ✅ Send Activity
                                    self.env["mail.activity"].create(
                                        {
                                            "res_model_id": self.env[
                                                "ir.model"
                                            ]._get_id("purchase.order"),
                                            "res_id": record.id,
                                            "activity_type_id": self.env.ref(
                                                "mail.mail_activity_data_todo"
                                            ).id,
                                            "summary": f"PO {record.name} has been {status}",
                                            "note": f"Dear Supervisor, the Purchase Order {record.name} has been {status.upper()}.",
                                            "user_id": self.env["res.partner"]
                                            .browse(supervisor_id_int)
                                            .user_ids[:1]
                                            .id,
                                        }
                                    )

                                    # ✅ Send Email
                                    mail_values = {
                                        "subject": f"Purchase Order {record.name} {status.upper()}",
                                        "body_html": f"""
                                                <p>Dear Supervisor,</p>
                                                <p>The Purchase Order <strong>{record.name}</strong> has been <strong>{status.upper()}</strong>.</p>
                                                <p>Thank you.</p>
                                            """,
                                        "email_to": self.env["res.partner"]
                                        .browse(supervisor_id_int)
                                        .email,
                                        "email_from": self.env.user.email
                                        or "noreply@yourcompany.com",
                                    }
                                    self.env["mail.mail"].sudo().create(
                                        mail_values
                                    ).send()

                                except ValueError:
                                    _logger.warning(
                                        "Invalid supervisor_partner_id: %s (not an integer)",
                                        supervisor_partner_id,
                                    )
                            else:
                                _logger.warning("No PR found with name: %s", pr_origin)
                    else:
                        _logger.info(
                            "No previous PO found with name: %s", record.origin
                        )

        return super(PurchaseOrder, self).write(vals)
