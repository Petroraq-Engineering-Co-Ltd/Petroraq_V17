from odoo import models, fields, api, _
from odoo.exceptions import AccessError
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
<<<<<<< HEAD
    expected_arrival = fields.Datetime(string="Quotation Date")
=======
    expected_arrival = fields.Datetime(string="Expected Arrival")
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f

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
<<<<<<< HEAD
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type", related="project_id.budget_type",
    )
    budget_code = fields.Char(string="Budget Code", related="project_id.budget_code")
=======
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type"
    )
    budget_code = fields.Char(string="Budget Code")
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f
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

<<<<<<< HEAD
    @api.depends("line_ids.price_unit", "line_ids.quantity")
    def _compute_totals(self):
        for record in self:
            total_excl = sum(
                line.price_unit * line.quantity for line in record.line_ids
=======
    @api.depends("line_ids.unit_price", "line_ids.quantity")
    def _compute_totals(self):
        for record in self:
            total_excl = sum(
                line.unit_price * line.quantity for line in record.line_ids
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f
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

#create purchase order
    def action_create_purchase_order(self):
        """Create Purchase Order from this Quotation in pending state with Custom Lines."""
        PurchaseOrder = self.env["purchase.order"]
        
        if self.budget_left < self.total_incl_vat:
<<<<<<< HEAD
             raise UserError(
                "Insufficient budget. You cannot proceed with Purchase Order creation."
            )

        for quotation in self:
            if not quotation.line_ids:
                raise UserError(_("This Quotation has no line items to create a Purchase Order."))
            
            matched_project = self.env["project.project"].search(
            [
                ("budget_type", "=", quotation.budget_type),
                ("budget_code", "=", quotation.budget_code),
            ],
            limit=1,
            )

            # Purchase Order values
            po_vals = {
                "origin": quotation.rfq_origin,
                "partner_id": quotation.vendor_id.id if quotation.vendor_id else False,
                "partner_ref": quotation.vendor_ref or "",
                "date_planned": quotation.delivery_date or fields.Datetime.now(),
                "project_id": matched_project.id if matched_project else False, 
                "custom_line_ids": [],
                "state": "pending", 
            }

            # Fill lines from Quotation Lines
            for line in quotation.line_ids:
                line_vals = (0, 0, {
                    "name": line.description or line.name,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "price_unit": line.price_unit,
                })
                po_vals["custom_line_ids"].append(line_vals)

            # Create Purchase Order
            po = PurchaseOrder.sudo().create(po_vals)

            # Log in chatter
            quotation.message_post(
                body=_("Purchase Order %s created from this Quotation and populated in Custom Lines tab.") % po.name,
                message_type="notification",
            )
            
        # 🔥 Approval workflow: assign reviewers based on amount
        amount = quotation.total_incl_vat
        group_xml_id = None

        if amount <= 10000:
            group_xml_id = "custom_user_portal.project_engineer"
        elif amount <= 100000:
            group_xml_id = "custom_user_portal.project_manager"
        elif amount <= 500000:
            group_xml_id = "custom_user_portal.operations_director"
        else:
            group_xml_id = "custom_user_portal.managing_director"
=======
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
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f

        if group_xml_id:
            group = self.env.ref(group_xml_id)
            for user in group.users:
<<<<<<< HEAD
                self.env["mail.activity"].create({
                    "res_model_id": self.env["ir.model"]._get("purchase.order").id,
                    "res_id": po.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "summary": "Review Purchase Order",
                    "user_id": user.id,
                    "note": f"Please review the Purchase Order for {po.name}.",
                    "date_deadline": fields.Date.today(),
                })
=======
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
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f

        return {
            "type": "ir.actions.act_window",
            "name": "Purchase Order",
            "res_model": "purchase.order",
<<<<<<< HEAD
            "res_id": po.id,
=======
            "res_id": purchase_order.id,
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f
            "view_mode": "form",
            "target": "current",
        }

<<<<<<< HEAD
=======
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
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f

    @api.model
    def create(self, vals):
        record = super(PurchaseQuotation, self).create(vals)

        # Define group references
        project_engineer_group = self.env.ref(
            "custom_user_portal.project_engineer", raise_if_not_found=False
        )
        project_manager_group = self.env.ref(
            "custom_user_portal.project_manager", raise_if_not_found=False
        )
        operations_director_group = self.env.ref(
            "custom_user_portal.operations_director", raise_if_not_found=False
        )
        managing_director_group = self.env.ref(
            "custom_user_portal.managing_director", raise_if_not_found=False
        )

        target_group = None

        if record.total_incl_vat <= 10000:
            target_group = project_engineer_group
        elif 10000 < record.total_incl_vat <= 100000:
            target_group = project_manager_group
        elif 100000 < record.total_incl_vat <= 500000:
            target_group = operations_director_group
        elif record.total_incl_vat > 500000:
            target_group = managing_director_group

        if target_group:
            for user in target_group.users:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary="New Purchase Quotation Created",
                    note=f"A new purchase quotation (ID: {record.id}) has been created with a total amount of {record.total_incl_vat:.2f}.",
                    user_id=user.id,
                )

        return record

class PurchaseQuotationLine(models.Model):
    _name = "purchase.quotation.line"
    _description = "Purchase Quotation Line"

<<<<<<< HEAD
    quotation_id = fields.Many2one("purchase.quotation", string="Quotation", ondelete="cascade")
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    price_unit = fields.Float(string="Unit Price")
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)
    tax_15 = fields.Float(string="15% Tax", compute="_compute_subtotal", store=True)
    grand_total = fields.Float(string="Grand Total", compute="_compute_subtotal", store=True)
    description = fields.Char(string="Description")

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
            line.tax_15 = line.subtotal * 0.15
            line.grand_total = line.subtotal + line.tax_15

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "RFQ Sent"),
            ("pending", "Pending Approval"),
            ("purchase", "Purchase Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        tracking=True,
    )
    project_id = fields.Many2one("project.project", string="Project")
    pe_approved = fields.Boolean(string="Approved", default=False)
    pm_approved = fields.Boolean(string="Approved", default=False)
    od_approved = fields.Boolean(string="Approved", default=False)
    md_approved = fields.Boolean(string="Approved", default=False)
    can_confirm_order = fields.Boolean(
        compute="_compute_can_confirm_order", store=False
    )
    # Computed fields for view visibility
    show_pe_approved = fields.Boolean(
        compute="_compute_show_approvals", store=False
    )
    show_pm_approved = fields.Boolean(
        compute="_compute_show_approvals", store=False
    )
    show_od_approved = fields.Boolean(
        compute="_compute_show_approvals", store=False
=======
    quotation_id = fields.Many2one("purchase.quotation", string="Quotation")
    product_id = fields.Many2one("product.product", string="Product")
    quantity = fields.Float(string="Quantity")
    unit_price = fields.Float(string="Unit Price")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    description = fields.Char()
    name = fields.Char()
    display_name_ui = fields.Char(
        string="Product", compute="_compute_display_name_ui", store=False
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f
    )
    show_md_approved = fields.Boolean(
        compute="_compute_show_approvals", store=False
    )
    subtotal = fields.Float(string="Subtotal", compute='_compute_amount_untaxed_custom', store=True)
    tax_15 = fields.Float(string="15% Tax", compute='_compute_amount_untaxed_custom', store=True)
    grand_total = fields.Float(string="Grand Total", compute='_compute_amount_untaxed_custom', store=True)
    custom_line_ids = fields.One2many(
        'purchase.order.custom.line',
        'order_id',                
        string='Custom Lines'
    )
    @api.depends('custom_line_ids.subtotal')
    def _compute_amount_untaxed_custom(self):
        for order in self:
            order.subtotal = sum(order.custom_line_ids.mapped('subtotal'))
            order.tax_15 = order.subtotal * 0.15
            order.grand_total = order.subtotal + order.tax_15

    def button_confirm(self):
        for order in self:
            if order.state == "pending":
                order.write({"state": "purchase"})
            else:
                super(PurchaseOrder, order).button_confirm()

    def _schedule_activity_for_group(self, group_xml_id, summary, note):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return
        for user in group.users:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=summary,
                note=note,
                user_id=user.id,
            )

    def action_approve(self):
        self.ensure_one()
        amount = self.subtotal

<<<<<<< HEAD
        if amount <= 10000:
            if not self.pe_approved:
                self.write({"pe_approved": True})
=======
    @api.depends("product_id", "name")
    def _compute_display_name_ui(self):
        for line in self:
            line.display_name_ui = (
                line.product_id.name if line.product_id else line.name
            )
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f

                self.message_post(body="Approved by Project Engineer.")
                return

<<<<<<< HEAD
        elif amount <= 100000:
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Project Engineer.")
                self._schedule_activity_for_group(
                    "custom_user_portal.project_manager",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PE. Please review.",
                )
            elif not self.pm_approved:
                self.write({"pm_approved": True})
                self.message_post(body="Approved by Project Manager.")

        elif amount <= 500000:
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Project Engineer.")
                self._schedule_activity_for_group(
                    "custom_user_portal.project_manager",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PE. Please review.",
                )
            elif not self.pm_approved:
                self.write({"pm_approved": True})
                self.message_post(body="Approved by Project Manager.")
                self._schedule_activity_for_group(
                    "custom_user_portal.operations_director",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PM. Please review.",
                )
            elif not self.od_approved:
                self.write({"od_approved": True})
                self.message_post(body="Approved by Operations Director.")

        else:  # Above 500k
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Project Engineer.")
                self._schedule_activity_for_group(
                    "custom_user_portal.project_manager",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PE. Please review.",
                )
            elif not self.pm_approved:
                self.write({"pm_approved": True})
                self.message_post(body="Approved by Project Manager.")
                self._schedule_activity_for_group(
                    "custom_user_portal.operations_director",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PM. Please review.",
                )
            elif not self.od_approved:
                self.write({"od_approved": True})
                self.message_post(body="Approved by Operations Director.")
                self._schedule_activity_for_group(
                    "custom_user_portal.managing_director",
                    "Review Purchase Order",
                    f"PO {self.name} approved by OD. Please review.",
                )
            elif not self.md_approved:
                self.write({"md_approved": True})
                self.message_post(body="Approved by Managing Director.")

    @api.depends(
        "state",
        "pe_approved",
        "pm_approved",
        "od_approved",
        "md_approved",
        "subtotal",
    )
    def _compute_can_confirm_order(self):
        for order in self:
            if order.state != "pending":
                order.can_confirm_order = False
                continue

            amt = order.subtotal
            if amt <= 10000:
                order.can_confirm_order = order.pe_approved
            elif amt <= 100000:
                order.can_confirm_order = order.pe_approved and order.pm_approved
            elif amt <= 500000:
                order.can_confirm_order = (
                    order.pe_approved and order.pm_approved and order.od_approved
                )
            else:
                order.can_confirm_order = (
                    order.pe_approved
                    and order.pm_approved
                    and order.od_approved
                    and order.md_approved
                )

    @api.depends("state")
    def _compute_show_approvals(self):
        """Compute visibility of approval fields based on user groups and state"""
        for order in self:
            user = self.env.user
            order.show_pe_approved = (
                order.state == "pending" and 
                user.has_group("custom_user_portal.project_engineer")
            )
            order.show_pm_approved = (
                order.state == "pending" and 
                user.has_group("custom_user_portal.project_manager")
            )
            order.show_od_approved = (
                order.state == "pending" and 
                user.has_group("custom_user_portal.operations_director")
            )
            order.show_md_approved = (
                order.state == "pending" and 
                user.has_group("custom_user_portal.managing_director")
            )

    def action_reject(self):
        for order in self:
            if not order.origin:
                raise UserError(_("This Purchase Order has no origin."))

            rejecting_user = self.env.user
            _logger.info(
                "Rejecting PO %s with origin: %s by %s",
                order.name,
                order.origin,
                rejecting_user.name,
            )

            # Step 1: Find the PO with this origin
            parent_po = self.env["purchase.order"].search(
                [("name", "=", order.origin)], limit=1
            )
            if not parent_po:
                _logger.warning("No parent PO found for origin: %s", order.origin)
                order.state = "cancel"
                continue

            _logger.info(
                "Origin %s belongs to PO %s with origin: %s",
                order.origin,
                parent_po.name,
                parent_po.origin,
            )

            # Step 2: Get the PR number from the parent PO origin
            if not parent_po.origin:
                _logger.warning("Parent PO %s has no origin.", parent_po.name)
                order.state = "cancel"
                continue

            pr_record = self.env["purchase.requisition"].search(
                [("name", "=", parent_po.origin)], limit=1
            )
            if not pr_record:
                _logger.warning(
                    "No Purchase Requisition found with name: %s", parent_po.origin
                )
                order.state = "cancel"
                continue

            _logger.info("Found PR %s linked to PO %s", pr_record.name, parent_po.name)

            # Step 3: Get supervisor_partner_id and convert to int
            if not pr_record.supervisor_partner_id:
                _logger.warning("PR %s has no supervisor_partner_id.", pr_record.name)
                order.state = "cancel"
                continue

            try:
                supervisor_id_int = int(pr_record.supervisor_partner_id)
            except ValueError:
                _logger.error(
                    "Supervisor Partner ID in PR %s is not a valid integer: %s",
                    pr_record.name,
                    pr_record.supervisor_partner_id,
                )
                order.state = "cancel"
                continue

            # Step 4: Find partner
            supervisor_partner = self.env["res.partner"].browse(supervisor_id_int)
            if not supervisor_partner.exists():
                _logger.warning("No partner found with ID: %s", supervisor_id_int)
            else:
                _logger.info(
                    "Supervisor Partner for PR %s is %s with email: %s",
                    pr_record.name,
                    supervisor_partner.name,
                    supervisor_partner.email,
                )

                # Create activity for supervisor
                self.env["mail.activity"].create(
                    {
                        "res_model_id": self.env["ir.model"]._get_id("purchase.order"),
                        "res_id": order.id,
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "user_id": (
                            supervisor_partner.user_ids[:1].id
                            if supervisor_partner.user_ids
                            else False
                        ),
                        "note": _("Purchase Order %s was rejected by %s")
                        % (order.name, rejecting_user.name),
                    }
                )

                # Send email to supervisor
                if supervisor_partner.email:
                    mail_values = {
                        "subject": _("Purchase Order %s Rejected") % order.name,
                        "body_html": _(
                            "<p>Hello %s,</p>"
                            "<p>The Purchase Order <b>%s</b> has been rejected by <b>%s</b>.</p>"
                            "<p>Regards,<br/>%s</p>"
                        )
                        % (
                            supervisor_partner.name,
                            order.name,
                            rejecting_user.name,
                            rejecting_user.company_id.name,
                        ),
                        "email_to": supervisor_partner.email,
                    }
                    self.env["mail.mail"].create(mail_values).send()

            # Final step: reject the current PO
            order.state = "cancel"
=======
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
>>>>>>> 88dd6242abcbcbf702324967f7ecb5db890c9d0f
