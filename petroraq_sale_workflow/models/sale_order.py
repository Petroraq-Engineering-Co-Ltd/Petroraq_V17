from copy import deepcopy

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import format_amount, html_escape

class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Quotation"

    approval_state = fields.Selection([
        ("draft", "Draft / Quotation"),
        ("to_manager", "Waiting Next Manager Approval"),
        ("to_md", "Waiting MD Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="draft", tracking=True, copy=False)

    manager_approver_id = fields.Many2one("res.users", string="Manager Approver", tracking=True)
    md_approver_id = fields.Many2one("res.users", string="MD Approver", tracking=True)
    approval_comment = fields.Text("Approval Comment", tracking=True)
    show_manager_approve_button = fields.Boolean(
        compute="_compute_show_approval_button_visibility",
        string="Show Manager Approve Button",
    )
    show_md_approve_button = fields.Boolean(
        compute="_compute_show_approval_button_visibility",
        string="Show MD Approve Button",
    )

    require_two_step = fields.Boolean(
        string="Require Two-Step Approval",
        compute="_compute_require_two_step",
        store=False,
    )
    section_subtotal_summary = fields.Html(
        string="Section Subtotals",
        compute="_compute_section_subtotal_summary",
        sanitize=False,
        help="Displays a summary of section subtotals and their grand total."
    )
    overhead_percent = fields.Float(
        string="Over Head (%)",
        default=0.0,
        digits=(16, 2),
        help="Percentage applied on the total amount to cover overhead costs."
    )
    overhead_amount = fields.Monetary(
        string="Over Head Amount",
        compute="_compute_buffer_amounts",
        currency_field="currency_id",
        store=False,
        help="Calculated overhead amount based on the total amount."
    )
    risk_percent = fields.Float(
        string="Risk (%)",
        default=0.0,
        digits=(16, 2),
        help="Percentage applied on the total amount to cover risk."
    )
    risk_amount = fields.Monetary(
        string="Risk Amount",
        compute="_compute_buffer_amounts",
        currency_field="currency_id",
        store=False,
        help="Calculated risk amount based on the total amount."
    )
    buffer_total_amount = fields.Monetary(
        string="Computed Total Amount",
        compute="_compute_buffer_amounts",
        currency_field="currency_id",
        store=False,
        help="Total amount including overhead and risk percentages."
    )
    profit_percent = fields.Float(
        string="Profit (%)",
        default=0.0,
        digits=(16, 2),
        help="Percentage applied on the grand total to compute profit."
    )
    profit_amount = fields.Monetary(
        string="Profit Amount",
        compute="_compute_profit_amount",
        currency_field="currency_id",
        store=False,
        help="Calculated profit amount based on the grand total."
    )
    profit_grand_total = fields.Monetary(
        string="Great Grand Total",
        compute="_compute_profit_amount",
        currency_field="currency_id",
        store=False,
        help="Grand total including profit."
    )
    @api.depends("amount_total", "company_id")
    def _compute_require_two_step(self):
        for order in self:
            company = order.company_id
            amt_mgr = company.sale_mgr_approval_min_amount or 0.0
            amt_md = company.sale_md_approval_min_amount or 0.0
            order.require_two_step = order.amount_total >= max(amt_mgr, amt_md)

    # --- Buttons / Actions ---

    @api.depends("approval_state", "manager_approver_id", "md_approver_id", "user_id", "create_uid")
    @api.depends_context("uid")
    def _compute_show_approval_button_visibility(self):
        current_user = self.env.user
        is_md_user = current_user.has_group("petroraq_sale_workflow.group_sale_approval_md")
        for order in self:
            creator = order.create_uid
            is_creator = creator and creator.id == current_user.id
            is_salesperson = order.user_id and order.user_id.id == current_user.id
            allow_self_approval = (not (is_creator or is_salesperson)) or is_md_user

            show_manager = False
            if order.approval_state == "to_manager" and allow_self_approval:
                if order.manager_approver_id and order.manager_approver_id.id == current_user.id:
                    show_manager = True
                elif is_md_user:
                    show_manager = True
            order.show_manager_approve_button = show_manager

            show_md = False
            if order.approval_state == "to_md" and allow_self_approval:
                if order.md_approver_id and order.md_approver_id.id == current_user.id:
                    show_md = True
            order.show_md_approve_button = show_md

    def action_request_manager_approval(self):
        for order in self:
            if order.state not in ("draft", "sent"):
                raise UserError(_("You can only request approval for quotations."))
            order.approval_state = "to_manager"
            order.message_post(body=_("Approval requested from Sales Manager."))
            if not order.manager_approver_id:
                creator = order.create_uid or order.user_id
                if creator and creator.parent_id:
                    order.manager_approver_id = creator.parent_id
                elif order.user_id and order.user_id.parent_id:
                    order.manager_approver_id = order.user_id.parent_id
            if order.manager_approver_id:
                order.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=order.manager_approver_id.id,
                    summary=_("Approve Sales Quotation"),
                )
        return True

    def action_manager_approve(self):
        self._check_is_manager()
        for order in self:
            if order.approval_state != "to_manager":
                raise UserError(_("This quotation is not awaiting manager approval."))
            company = order.company_id
            if order.amount_total >= (company.sale_md_approval_min_amount or 0.0):
                order.approval_state = "to_md"
                order.md_approver_id = order.company_id.sale_md_user_id
                if order.md_approver_id:
                    order.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=order.md_approver_id.id,
                        summary=_("Approve Sales Quotation (MD)"),
                    )
            else:
                order.approval_state = "approved"
            order.message_post(body=_("Approved by Manager."))
        return True

    def action_md_approve(self):
        self._check_is_md()
        for order in self:
            if order.approval_state != "to_md":
                raise UserError(_("This quotation is not awaiting MD approval."))
            order.approval_state = "approved"
            order.message_post(body=_("Approved by MD."))
        return True

    def action_reject(self):
        self._check_is_approver()
        for order in self:
            if order.approval_state not in ("to_manager", "to_md"):
                raise UserError(_("Only waiting approvals can be rejected."))
            order.approval_state = "rejected"
            order.message_post(body=_("Quotation has been rejected."))
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_order_id": self.id,
            },
        }

    def action_reset_to_draft(self):
        for order in self:
            order.approval_state = "draft"
        return super().action_reset_to_draft()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        auto_orders = orders.filtered(lambda o: o.approval_state == "draft")
        if auto_orders:
            # auto trigger approval request so process starts without manual action
            auto_orders.action_request_manager_approval()
        return orders

    @api.model
    def default_get(self, fields_list):
        """Set a sensible default payment term for new quotations (module-provided).
        Falls back to the regular default if the data record is not available.
        """
        defaults = super().default_get(fields_list)
        # only set default if not already provided
        if "payment_term_id" not in defaults or not defaults.get("payment_term_id"):
            try:
                term = self.env.ref("petroraq_sale_workflow.payment_term_immediate")
                if term and term.id:
                    defaults["payment_term_id"] = term.id
            except ValueError:
                # reference may not exist (data not loaded); ignore
                pass
        return defaults

    # Block sending and confirmation until approved
    def action_quotation_send(self):
        for order in self:
            if order.approval_state != "approved":
                raise UserError(_("You can only send the quotation to the customer after final approval."))
        return super().action_quotation_send()

    def action_confirm(self):
        for order in self:
            if order.approval_state != "approved":
                raise UserError(_("You cannot confirm the order before final approval."))
        return super().action_confirm()

    @api.depends("amount_total", "currency_id", "overhead_percent", "risk_percent")
    def _compute_buffer_amounts(self):
        for order in self:
            base_amount = order.amount_total or 0.0
            overhead_pct = order.overhead_percent or 0.0
            risk_pct = order.risk_percent or 0.0
            currency = order.currency_id or order.company_id.currency_id

            overhead_amount = base_amount * overhead_pct / 100.0
            risk_amount = base_amount * risk_pct / 100.0

            if currency:
                overhead_amount = currency.round(overhead_amount)
                risk_amount = currency.round(risk_amount)
                buffer_total = currency.round(base_amount + overhead_amount + risk_amount)
            else:
                buffer_total = base_amount + overhead_amount + risk_amount

            order.overhead_amount = overhead_amount
            order.risk_amount = risk_amount
            order.buffer_total_amount = buffer_total
        self._compute_profit_amount()

    @api.depends(
        "buffer_total_amount",
        "amount_total",
        "currency_id",
        "profit_percent",
    )
    def _compute_profit_amount(self):
        for order in self:
            base = order.buffer_total_amount if order.buffer_total_amount or order.buffer_total_amount == 0.0 else order.amount_total
            profit_pct = order.profit_percent or 0.0
            currency = order.currency_id or order.company_id.currency_id
            profit_amount = base * profit_pct / 100.0
            if currency:
                profit_amount = currency.round(profit_amount)
                grand_total = currency.round((base or 0.0) + profit_amount)
            else:
                grand_total = (base or 0.0) + profit_amount
            order.profit_amount = profit_amount
            order.profit_grand_total = grand_total

    @api.depends(
        "amount_total",
        "currency_id",
        "overhead_percent",
        "risk_percent",
        "buffer_total_amount",
        "profit_percent",
        "profit_grand_total",
    )
    def _compute_section_subtotal_summary(self):
        total_label = _("Total Amount")
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            total_value = order.profit_grand_total if order.profit_grand_total or order.profit_grand_total == 0.0 else order.buffer_total_amount or order.amount_total
            if currency:
                total_display = format_amount(order.env, total_value or 0.0, currency)
            else:
                total_display = f"{(total_value or 0.0):.2f}"
            order.section_subtotal_summary = (
                "<div class='o_section_total_summary'>"
                f"<span class='o_section_total_label'>{html_escape(total_label)}</span>"
                f"<span class='o_section_total_value'>{html_escape(total_display)}</span>"
                "</div>"
            )

    @api.depends_context("lang")
    @api.depends("order_line.tax_id", "order_line.price_unit", "amount_total", "amount_untaxed", "currency_id")
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            if not order.tax_totals:
                continue

            tax_totals = deepcopy(order.tax_totals)
            untaxed_label = _("Untaxed Amount")
            desired_label = _("Total Amount")
            removal_labels = {_("Tax 15%"), "Tax 15%"}

            # Rename the subtotal label in the widget output.
            for subtotal in tax_totals.get("subtotals", []):
                if subtotal.get("name") == untaxed_label:
                    subtotal["name"] = desired_label

            groups_by_subtotal = tax_totals.get("groups_by_subtotal") or {}
            for key, group_list in list(groups_by_subtotal.items()):
                filtered_groups = [
                    tax_group
                    for tax_group in group_list
                    if tax_group.get("tax_group_name") not in removal_labels
                ]
                groups_by_subtotal[key] = filtered_groups
                if key == untaxed_label:
                    groups_by_subtotal[desired_label] = filtered_groups

            subtotals_order = tax_totals.get("subtotals_order")
            if subtotals_order:
                tax_totals["subtotals_order"] = [
                    desired_label if name == untaxed_label else name
                    for name in subtotals_order
                ]

            order.tax_totals = tax_totals

    @api.constrains("payment_term_id")
    def _check_payment_term_selectable(self):
        for order in self:
            term = order.payment_term_id
            if term and not getattr(term, "petroraq_selectable", False):
                raise UserError(_("The selected payment term is not allowed. Please choose one of the Petroraq payment terms."))

    # --- Security helpers ---
    def _check_is_manager(self):
        if not (
            self.env.user.has_group("petroraq_sale_workflow.group_sale_approval_manager")
            or self.env.user.has_group("sales_team.group_sale_manager")
            or self.env.user.has_group("petroraq_sale_workflow.group_sale_approval_md")
        ):
            raise AccessError(_("Only Sales Manager/Approver can validate this step."))

    def _check_is_md(self):
        if not self.env.user.has_group("petroraq_sale_workflow.group_sale_approval_md"):
            raise AccessError(_("Only MD/Final Authority can validate this step."))

    def _check_is_approver(self):
        if not (
            self.env.user.has_group("petroraq_sale_workflow.group_sale_approval_manager")
            or self.env.user.has_group("petroraq_sale_workflow.group_sale_approval_md")
            or self.env.user.has_group("sales_team.group_sale_manager")
        ):
            raise AccessError(_("Only approvers can reject approvals."))


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    section_subtotal_amount = fields.Monetary(
        string="Section Subtotal",
        compute="_compute_section_subtotal_amount",
        store=False,
        currency_field="currency_id",
        help="Subtotal of the products within this section."
    )
    section_subtotal_display = fields.Html(
        string="Section Subtotal Display",
        compute="_compute_section_subtotal_amount",
        sanitize=False,
        help="Formatted subtotal snippet for section headers."
    )

    @api.depends(
        "display_type",
        "price_subtotal",
        "sequence",
        "order_id.order_line.price_subtotal",
        "order_id.order_line.display_type",
        "order_id.order_line.sequence",
    )
    def _compute_section_subtotal_amount(self):
        label = _("Sub Total")
        for line in self:
            line.section_subtotal_amount = 0.0
            line.section_subtotal_display = False

        for order in self.mapped("order_id"):
            subtotal = 0.0
            current_section = None
            ordered_lines = order.order_line.sorted(key=lambda l: (l.sequence or 0, l.id or 0))
            for line in ordered_lines:
                if line.display_type == "line_section":
                    if current_section:
                        current_section._set_section_subtotal_values(subtotal, label)
                    current_section = line
                    subtotal = 0.0
                    line.section_subtotal_amount = 0.0
                    line.section_subtotal_display = False
                elif line.display_type:
                    continue
                else:
                    subtotal += line.price_subtotal
            if current_section:
                current_section._set_section_subtotal_values(subtotal, label)

    def _set_section_subtotal_values(self, amount, label):
        self.ensure_one()
        currency = self.order_id.currency_id or self.order_id.company_id.currency_id
        if currency:
            amount_display = format_amount(self.env, amount, currency)
        else:
            amount_display = f"{amount:.2f}"
        self.section_subtotal_amount = amount
        self.section_subtotal_display = (
            f"<span class='o_section_subtotal_chip_label'>{html_escape(label)}</span>"
            f"<span class='o_section_subtotal_chip_value'>{html_escape(amount_display)}</span>"
        )


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_mgr_approval_min_amount = fields.Monetary(
        string="Manager Approval From Amount",
        help="If total is >= this amount, manager approval is required.")
    sale_md_approval_min_amount = fields.Monetary(
        string="MD Approval From Amount",
        help="If total is >= this amount, MD approval is required (after manager).")
    sale_md_user_id = fields.Many2one("res.users", string="Default MD Approver")
