from copy import deepcopy

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_amount, html_escape


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Quotation"

    approval_state = fields.Selection([
        ("draft", "Draft"),
        ("to_manager", "Manager Approve"),
        ("to_md", "MD Approve"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="draft", tracking=True, copy=False)

    dp_percent = fields.Float(
        string="Down Payment %",
        copy=False,
    )
    po_date = fields.Date(
        string="PO Date",
        copy=False,
    )
    po_number = fields.Char(
        string="PO Number",
        copy=False,
    )

    section_subtotal_summary = fields.Html(
        string="Section Subtotals",
        compute="_compute_section_subtotal_summary",
        sanitize=False,
        help="Displays a summary of section subtotals and their grand total."
    )
    inquiry_type = fields.Selection([('construction', 'Contracting'), ('trading', 'Trading')], string="Inquiry Type",
                                    default="trading", )

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
    approval_comment = fields.Text("Approval Comment", tracking=True)

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
        store=True,
        help="Calculated profit amount based on the grand total."
    )
    profit_grand_total = fields.Monetary(
        string="Net Total",
        compute="_compute_profit_amount",
        currency_field="currency_id",
        store=True,
        help="Grand total including profit."
    )
    proforma_dp = fields.Integer(
        string="Down payment Percentage",
        store=True,
        help="The amount of Advance payment required upon the order confirmation."
    )

    final_grand_total = fields.Monetary(
        string="Grand Taxed Total",
        compute="_compute_final_totals",
        currency_field="currency_id",
        store=True,
        help="Grand total including profit."
    )

    payment_term_domain = fields.Char(
        compute="_compute_payment_term_domain",
        store=False,
    )

    @api.onchange("inquiry_type")
    def _onchange_inquiry_type_payment_term(self):
        for order in self:
            term = order.payment_term_id
            if not order.inquiry_type:
                continue

            # if current selection is not allowed -> reset to a valid default
            if order.inquiry_type == "trading":
                if term and not term.is_trading_term:
                    order.payment_term_id = False
                if not order.payment_term_id:
                    order.payment_term_id = self.env.ref(
                        "petroraq_sale_workflow.payment_term_trading_advance",
                        raise_if_not_found=False
                    )
            else:
                if term and term.is_trading_term:
                    order.payment_term_id = False
                if not order.payment_term_id:
                    order.payment_term_id = self.env.ref(
                        "petroraq_sale_workflow.payment_term_immediate",
                        raise_if_not_found=False
                    )

    @api.depends("inquiry_type")
    def _compute_payment_term_domain(self):
        for order in self:
            if order.inquiry_type == "trading":
                order.payment_term_domain = "[('petroraq_selectable','=',True),('is_trading_term','=',True)]"
            else:
                order.payment_term_domain = "[('petroraq_selectable','=',True),('is_trading_term','=',False)]"

    @api.constrains("proforma_dp")
    def _check_proforma_dp(self):
        for order in self:
            if order.proforma_dp > 100 or order.proforma_dp < 0:
                raise UserError(_("Down payment percentage must be between 0 and 100"))

    @api.depends("order_line", "overhead_percent", "risk_percent", "profit_percent", "currency_id")
    def _compute_final_totals(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            rounding_method = order.company_id.tax_calculation_rounding_method  # 'round_globally' or 'round_per_line'

            total = 0.0
            vat_sum = 0.0

            normal_lines = order.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)

            for line in normal_lines:
                qty = line.product_uom_qty or 0.0

                base = line.price_unit or 0.0
                base_r = currency.round(base)

                oh_r = currency.round(base_r * (order.overhead_percent or 0.0) / 100.0)
                risk_r = currency.round(base_r * (order.risk_percent or 0.0) / 100.0)

                unit_or_r = currency.round(base_r + oh_r + risk_r)
                profit_r = currency.round(unit_or_r * (order.profit_percent or 0.0) / 100.0)

                final_unit_r = currency.round(unit_or_r + profit_r)
                line_total_r = currency.round(final_unit_r * qty)

                total += line_total_r

                if rounding_method == "round_per_line":
                    vat_sum += currency.round(line_total_r * 0.15)

            if rounding_method != "round_per_line":
                vat_sum = currency.round(total * 0.15)

            order.final_grand_total = currency.round(total + vat_sum)

    def _costing_total_no_vat_without_profit(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        total = 0.0
        lines = self.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)

        for l in lines:
            base = l.price_unit or 0.0
            qty = l.product_uom_qty or 0.0

            oh = base * (self.overhead_percent or 0.0) / 100.0
            risk = base * (self.risk_percent or 0.0) / 100.0
            unit_or = base + oh + risk

            unit_or_r = currency.round(unit_or)
            line_total_r = currency.round(unit_or_r * qty)

            total += line_total_r

        return total

    def _costing_total_no_vat(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        total = 0.0
        lines = self.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
        for l in lines:
            base = l.price_unit or 0.0
            qty = l.product_uom_qty or 0.0

            final_unit = self._costing_final_unit(base)
            final_unit_r = currency.round(final_unit)
            line_total_r = currency.round(final_unit_r * qty)

            total += line_total_r

        return total

    @api.depends("amount_total", "company_id")
    def _compute_require_two_step(self):
        for order in self:
            company = order.company_id
            amt_mgr = company.sale_mgr_approval_min_amount or 0.0
            amt_md = company.sale_md_approval_min_amount or 0.0
            order.require_two_step = order.amount_total >= max(amt_mgr, amt_md)

    show_reject_button = fields.Boolean(compute="_compute_show_reject_button")

    @api.model
    def translate_sale_name(self, name):
        if not name:
            return ""
        numerals_map = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
        return str(name).translate(numerals_map)

    @api.model
    def convert_phone_to_eastern_arabic_numerals(self, value):
        if not value:
            return ""
        numerals_map = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
        return str(value).translate(numerals_map)

    @api.depends_context("uid")
    @api.depends("approval_state")
    def _compute_show_reject_button(self):
        user = self.env.user

        for order in self:
            order.show_reject_button = (
                    (order.approval_state == "to_manager" and user.has_group(
                        "petroraq_sale_workflow.group_sale_approval_manager"))
                    or
                    (order.approval_state == "to_md" and user.has_group(
                        "petroraq_sale_workflow.group_sale_approval_md"))
            )

    def action_manager_approve(self):
        for order in self:
            if order.approval_state != "to_manager":
                raise UserError(_("This quotation is not awaiting manager approval."))

            order.approval_state = "to_md"
            order.locked = True

    def action_confirm_quotation(self):
        for order in self:
            if not order.order_line:
                raise UserError(_("Please add at least one line item to the quotation."))
        self.approval_state = "to_manager"
        self.state = "draft"
        self.approval_comment = False

    def action_md_approve(self):
        for order in self:
            if order.approval_state != "to_md":
                raise UserError(_("This quotation is not awaiting MD approval."))
            order.approval_state = "approved"

        return True

    def action_reject(self):
        for order in self:
            if order.approval_state not in ("to_manager", "to_md", "draft"):
                raise UserError(_("Only waiting approvals can be rejected."))
            order.approval_state = "rejected"
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

    def action_draft(self):
        res = super().action_draft()

        for order in self:
            order.locked = False
            order.approval_state = "draft"

        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        for order in self:
            order.locked = False
            order.approval_state = "rejected"
        return res

    def action_reset_to_draft(self):
        for order in self:
            if order.approval_state == "rejected":
                order.locked = False
                order.approval_state = "draft"

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        inquiry = defaults.get("inquiry_type", "trading")

        if "payment_term_id" in fields_list and not defaults.get("payment_term_id"):
            if inquiry == "trading":
                xmlid = "petroraq_sale_workflow.payment_term_trading_advance"
            else:
                xmlid = "petroraq_sale_workflow.payment_term_immediate"

            term = self.env.ref(xmlid, raise_if_not_found=False)
            if term:
                defaults["payment_term_id"] = term.id

        return defaults

    def action_quotation_send(self):
        self.ensure_one()

        if self.approval_state != "approved":
            raise UserError(_("You can only send the quotation to the customer after final approval."))

        self.order_line._validate_analytic_distribution()

        lang = self.env.context.get("lang")

        if self.env.context.get("proforma"):
            mail_template = self.env.ref(
                "petroraq_sale_workflow.petroraq_custom_proforma_email",
                raise_if_not_found=False,
            )
        else:
            mail_template = self.env.ref(
                "petroraq_sale_workflow.petroraq_custom_sale_email",
                raise_if_not_found=False,
            ) or self._find_mail_template()

        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]

        # ✅ build recipients (partners only)
        partner_ids = []
        if self.partner_id:
            partner_ids.append(self.partner_id.id)

        # if quotation came from inquiry, add that inquiry contact partner
        if self.order_inquiry_id and self.order_inquiry_id.contact_partner_id:
            partner_ids.append(self.order_inquiry_id.contact_partner_id.id)

        ctx = {
            "default_model": "sale.order",
            "default_res_ids": self.ids,
            "default_template_id": mail_template.id if mail_template else None,
            "default_composition_mode": "comment",
            "mark_so_as_sent": True,
            "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
            "proforma": self.env.context.get("proforma", False),
            "force_email": True,
            "model_description": self.with_context(lang=lang).type_name,

            # ✅ auto-select recipients in wizard
            "default_partner_ids": [(6, 0, list(set(partner_ids)))],
        }

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "target": "new",
            "context": ctx,
        }

    def _costing_final_unit(self, base):
        """Return final unit (OH + risk + profit) using SAME rounding pipeline as QWeb/invoice."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        base_r = currency.round(base or 0.0)

        oh_r = currency.round(base_r * (self.overhead_percent or 0.0) / 100.0)
        risk_r = currency.round(base_r * (self.risk_percent or 0.0) / 100.0)

        unit_or_r = currency.round(base_r + oh_r + risk_r)
        profit_r = currency.round(unit_or_r * (self.profit_percent or 0.0) / 100.0)

        return currency.round(unit_or_r + profit_r)

    def _costing_line_total(self):
        self.ensure_one()
        order = self.order_id
        currency = order.currency_id or order.company_id.currency_id
        unit_r = self._costing_final_unit()
        qty = self.product_uom_qty or 0.0
        return currency.round(unit_r * qty)

    def action_confirm(self):
        for order in self:
            if not order.order_line:
                raise UserError(_("Please add at least one line item to the quotation."))
            if order.approval_state != "approved":
                raise UserError(_("You cannot confirm the order before final approval."))

        locked_orders = self.filtered('locked')
        if locked_orders:
            locked_orders.action_unlock()

        try:
            res = super().action_confirm()
        finally:
            if locked_orders:
                locked_orders.action_lock()

        return res

    @api.depends(
        "order_line.display_type",
        "order_line.is_downpayment",
        "order_line.price_unit",
        "order_line.product_uom_qty",
        "overhead_percent",
        "risk_percent",
        "profit_percent",
        "currency_id",
    )
    def _compute_buffer_amounts(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id

            base_total = oh_total = risk_total = profit_total = grand_total = 0.0

            lines = order.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
            for l in lines:
                qty = l.product_uom_qty or 0.0
                base = l.price_unit or 0.0

                # 1) round per unit
                base_u = currency.round(base)
                oh_u = currency.round(base * (order.overhead_percent or 0.0) / 100.0)
                risk_u = currency.round(base * (order.risk_percent or 0.0) / 100.0)

                unit_or = currency.round(base_u + oh_u + risk_u)

                # 2) profit per unit, rounded
                profit_u = currency.round(unit_or * (order.profit_percent or 0.0) / 100.0)

                # 3) final unit rounded (matches “16.54” behavior)
                final_u = currency.round(unit_or + profit_u)

                # 4) totals per line (multiply then round)
                base_total += currency.round(base_u * qty)
                oh_total += currency.round(oh_u * qty)
                risk_total += currency.round(risk_u * qty)
                profit_total += currency.round(profit_u * qty)
                grand_total += currency.round(final_u * qty)

            order.overhead_amount = oh_total
            order.risk_amount = risk_total
            order.buffer_total_amount = base_total + oh_total + risk_total

            order.profit_amount = profit_total
            order.profit_grand_total = grand_total

    @api.depends("order_line", "overhead_percent", "risk_percent", "profit_percent", "currency_id")
    def _compute_profit_amount(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id

            buffer_total = order._costing_total_no_vat_without_profit()  # new helper (see below)
            grand_no_vat = order._costing_total_no_vat()  # already exists (with profit)

            order.buffer_total_amount = buffer_total
            order.profit_grand_total = grand_no_vat
            order.profit_amount = currency.round(grand_no_vat - buffer_total)

    @api.depends(
        "amount_total",
        "currency_id",
        "overhead_percent",
        "risk_percent",
        "buffer_total_amount",
        "profit_percent",
        "profit_grand_total",
        "amount_untaxed",
    )
    def _compute_section_subtotal_summary(self):
        total_label = _("Total Amount")
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            total_value = order.profit_grand_total if order.profit_grand_total or order.profit_grand_total == 0.0 else order.buffer_total_amount or order.amount_untaxed
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

    @api.constrains("payment_term_id", "inquiry_type")
    def _check_payment_term_selectable(self):
        for order in self:
            term = order.payment_term_id
            if not term:
                raise UserError(_("Please select a payment term before saving the quotation."))

            if not getattr(term, "petroraq_selectable", False):
                raise UserError(
                    _("The selected payment term is not allowed. Please choose one of the Petroraq payment terms."))

            # ✅ Trading rule
            if order.inquiry_type == "trading":
                if not term.is_trading_term:
                    raise UserError(_("For Trading inquiries, only Advance and Credit payment terms are allowed."))
            else:
                if term.is_trading_term:
                    raise UserError(_("Advance/Credit payment terms are only allowed for Trading inquiries."))


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for picking in self:
            # Only for outgoing deliveries
            if picking.picking_type_code != 'outgoing':
                continue

            sale = picking.sale_id
            if not sale:
                continue

            if sale.payment_term_id and sale.payment_term_id.name.lower() == 'advance':
                dp_invoices = sale.invoice_ids.filtered(
                    lambda inv:
                    inv.state == 'posted'
                    and inv.move_type == 'out_invoice'
                    and any(
                        line.sale_line_ids.is_downpayment
                        for line in inv.invoice_line_ids
                    )
                )

                if not dp_invoices:
                    raise UserError(_(
                        "You cannot validate this delivery.\n\n"
                        "A Down Payment invoice is required for Advance orders."
                    ))

                unpaid = dp_invoices.filtered(
                    lambda inv: inv.payment_state != 'in_payment')
                if unpaid:
                    raise UserError(_(
                        "You cannot validate this delivery.\n\n"
                        "The Down Payment invoice must be fully paid."
                    ))

        return super().button_validate()
