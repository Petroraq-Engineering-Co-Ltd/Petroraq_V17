# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountJournalVoucher(models.Model):
    # region [Initial]
    _name = "pr.account.journal.voucher"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Journal Voucher"
    _order = "id"
    _rec_name = "name"
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string="Number", tracking=True)

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        index=True,
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        tracking=True,
    )

    accounting_date = fields.Date(
        string="Date",
        required=True,
        tracking=True,
        default=fields.Date.today,
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self.env['account.journal'].search([
            ('id', '=', '3'),
            ('company_id', '=', self.env.company.id)
        ], limit=1).id,
        tracking=True,
    )

    description = fields.Text(string="Description", tracking=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submit", "Submitted"),
            ("supervisor_approve", "Supervisor Approved"),
            ("manager_approve", "Manager Approved"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        tracking=True,
        default="draft",
    )

    line_ids = fields.One2many(
        "pr.account.journal.voucher.line",
        "voucher_id",
        string="Lines",
    )

    total_debit = fields.Float(
        string="Total Debit",
        compute="_compute_totals",
        store=True,
        tracking=True,
    )

    total_credit = fields.Float(
        string="Total Credit",
        compute="_compute_totals",
        store=True,
        tracking=True,
    )

    balance_difference = fields.Float(
        string="Difference (Dr - Cr)",
        compute="_compute_totals",
        store=True,
        tracking=True,
    )

    journal_entry_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        tracking=True,
    )

    # endregion [Fields]

    # region [Constraints]

    @api.constrains("company_id")
    def _check_company(self):
        for rec in self:
            if rec.company_id and rec.company_id.id != self.env.company.id:
                raise ValidationError(
                    _("You should select the current company, please check!")
                )

    @api.constrains("line_ids")
    def _check_positive_amount_line(self):
        for rec in self:
            lines = rec.line_ids

            if not lines:
                raise ValidationError(_("You must add at least one line with a positive amount."))

            if all(line.total_amount <= 0 for line in lines):
                raise ValidationError(_("At least one line must have a positive amount."))

    # endregion [Constraints]

    # region [Compute]

    @api.depends("line_ids", "line_ids.debit", "line_ids.credit")
    def _compute_totals(self):
        for rec in self:
            debit = credit = 0.0
            for line in rec.line_ids:
                debit += line.debit or 0.0
                credit += line.credit or 0.0
            rec.total_debit = debit
            rec.total_credit = credit
            rec.balance_difference = debit - credit

    # endregion [Compute]

    # region [Helpers]

    def _check_balanced_lines(self):
        """Ensure total debit == total credit."""
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("You must add at least one line."))
            precision = rec.currency_id.rounding if rec.currency_id else 0.01
            if (
                    float_compare(
                        rec.total_debit,
                        rec.total_credit,
                        precision_rounding=precision,
                    )
                    != 0
            ):
                raise ValidationError(
                    _(
                        "Journal Voucher is not balanced.\n"
                        "Debit: %(debit).2f  |  Credit: %(credit).2f"
                    )
                    % {"debit": rec.total_debit, "credit": rec.total_credit}
                )

    # endregion [Helpers]

    # region [Workflow Actions]

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise ValidationError(_("Only Draft vouchers can be submitted."))
            if not rec.line_ids:
                raise ValidationError(_("You must add at least one line."))
            rec.state = "submit"

    def action_supervisor_approve(self):
        for rec in self:
            if rec.state != "submit":
                raise ValidationError(
                    _("Only Submitted vouchers can be approved by Supervisor.")
                )
            rec.state = "supervisor_approve"

    def action_manager_approve(self):
        for rec in self:
            if rec.state != "supervisor_approve":
                raise ValidationError(
                    _("Only Supervisor Approved vouchers can be approved by Manager.")
                )

            # First set state
            rec.state = "manager_approve"

            # ---------- AUTO POST ----------
            rec._check_balanced_lines()

            move_vals = {
                "ref": rec.name,
                "date": rec.accounting_date,
                "journal_id": rec.journal_id.id,
                "move_type": "entry",
                "company_id": rec.company_id.id,
            }

            move = (
                self.env["account.move"]
                .with_context(check_move_validity=False, skip_invoice_sync=True)
                .create(move_vals)
            )

            line_model = self.env["account.move.line"].with_context(
                check_move_validity=False, skip_invoice_sync=True
            )

            for line in rec.line_ids:
                line_vals = {
                    "move_id": move.id,
                    "account_id": line.account_id.id,
                    "name": line.description or (rec.description or "/"),
                    "debit": line.debit,
                    "credit": line.credit,
                    "partner_id": line.partner_id.id or False,
                    "analytic_distribution": line.analytic_distribution or False,
                    "cs_project_id": line.cs_project_id.id or False,
                    "cs_employee_id": line.cs_employee_id.id or False,
                    "asset_id": line.asset_id.id or False,
                    "tax_ids": [(6, 0, line.tax_ids.ids)],
                }
                line_model.create(line_vals)

            # Post JE
            move.action_post()

            # Link JE
            rec.journal_entry_id = move.id

            # Final state
            rec.state = "posted"

    def action_reset_to_draft(self):
        for rec in self:

            # Allow reset from ANY state except draft
            if rec.state == "draft":
                raise ValidationError(_("Already in Draft."))

            if rec.journal_entry_id:
                move = rec.journal_entry_id.sudo()

                if move.state == "posted":
                    move.button_draft()

                move.unlink()

                rec.journal_entry_id = False

            rec.state = "draft"

    def action_cancel(self):
        for rec in self:
            if rec.state == "posted" and rec.journal_entry_id:
                # Cancel JE as well
                if rec.journal_entry_id.state == "posted":
                    rec.journal_entry_id.sudo().button_draft()
                rec.journal_entry_id.sudo().button_cancel()
            rec.state = "cancel"

    def action_post(self):
        """Manager final approval + create/post JE."""
        for rec in self:
            if rec.state != "manager_approve":
                raise ValidationError(
                    _("Only Manager Approved vouchers can be posted.")
                )

            rec._check_balanced_lines()

            move_vals = {
                "ref": rec.name,
                "date": rec.accounting_date,
                "journal_id": rec.journal_id.id,
                "move_type": "entry",
                "company_id": rec.company_id.id,
            }
            move = (
                self.env["account.move"]
                .with_context(check_move_validity=False, skip_invoice_sync=True)
                .create(move_vals)
            )

            line_model = self.env["account.move.line"].with_context(
                check_move_validity=False, skip_invoice_sync=True
            )

            for line in rec.line_ids:
                line_vals = {
                    "move_id": move.id,
                    "account_id": line.account_id.id,
                    "name": line.description or (rec.description or "/"),
                    "debit": line.debit,
                    "credit": line.credit,
                    "partner_id": line.partner_id.id if line.partner_id else False,
                    "analytic_distribution": line.analytic_distribution or False,
                    "cs_project_id": line.cs_project_id.id
                    if line.cs_project_id
                    else False,
                }
                line_model.create(line_vals)

            move.action_post()
            rec.journal_entry_id = move.id
            rec.state = "posted"

    def open_journal_entry(self):
        self.ensure_one()
        if not self.journal_entry_id:
            raise ValidationError(_("No journal entry linked to this Journal Voucher."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entry"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.journal_entry_id.id,
        }

    # endregion [Workflow Actions]

    # region [CRUD]

    @api.model
    def create(self, vals):
        if vals.get('name'):
            vals['name'] = False

        res = super().create(vals)

        if not res.name:
            res.name = self.env["ir.sequence"].next_by_code(
                "pr.account.journal.voucher.seq.code"
            )

        return res

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise ValidationError(
                    _("Only Draft Journal Vouchers can be deleted.")
                )
            if rec.journal_entry_id:
                raise ValidationError(
                    _("You cannot delete a voucher linked to a Journal Entry.")
                )
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})

        default['name'] = False
        default['journal_entry_id'] = False

        default['line_ids'] = [
            (0, 0, {
                'account_id': l.account_id.id,
                'cs_project_id': l.cs_project_id.id,
                'partner_id': l.partner_id.id,
                'cs_employee_id': l.cs_employee_id.id,
                'asset_id': l.asset_id.id,
                'description': l.description,
                'reference_number': l.reference_number,
                'analytic_distribution': l.analytic_distribution,
                'debit': l.debit,
                'credit': l.credit,
                'tax_ids': [(6, 0, l.tax_ids.ids)],
            })
            for l in self.line_ids
        ]

        return super().copy(default)

    # endregion [CRUD]




class AccountJournalVoucherLine(models.Model):
    # region [Initial]
    _name = "pr.account.journal.voucher.line"
    _description = "Journal Voucher Line"
    # endregion [Initial]

    # region [Fields]

    voucher_id = fields.Many2one(
        "pr.account.journal.voucher",
        string="Journal Voucher",
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="voucher_id.company_id",
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="voucher_id.currency_id",
        store=True,
    )

    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        ondelete="restrict",
        index=True,
    )

    account_name = fields.Char(
        string="Account Name",
        related="account_id.name",
        store=True,
    )

    cs_project_id = fields.Many2one(
        "account.analytic.account",
        string="Project",
        domain="[('analytic_plan_type', '=', 'project')]",
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Project Manager",
        tracking=True,
    )
    cs_employee_id = fields.Many2one("account.analytic.account", string="Employee",
                                     domain="[('analytic_plan_type', '=', 'employee')]")

    asset_id = fields.Many2one('account.analytic.account', string="Asset",
                               domain="[('analytic_plan_type', '=', 'asset')]")

    tax_ids = fields.Many2many(
        "account.tax",
        string="Tax Grids",
        domain="[('type_tax_use','in',('sale','purchase'))]"
    )

    description = fields.Text(string="Description", tracking=True)

    reference_number = fields.Char(string="Reference Number")

    analytic_distribution = fields.Json(string="Cost Centers")

    analytic_precision = fields.Integer(
        string="Analytic Precision",
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )

    analytic_accounting_date = fields.Date(
        string="Analytic Accounting Date",
        related="voucher_id.accounting_date",
        store=False,
    )

    debit = fields.Float(string="Debit", tracking=True)
    credit = fields.Float(string="Credit", tracking=True)

    check_cost_centers_block = fields.Boolean(
        compute="_compute_check_cost_centers_block",
        string="Block CC?",
    )

    # endregion [Fields]

    # region [Onchange / Compute]

    @api.depends("account_id", "account_id.main_head")
    @api.onchange("account_id", "account_id.main_head")
    def _compute_check_cost_centers_block(self):
        for line in self:
            if line.account_id and line.account_id.main_head in [
                "revenue",
                "expense",
            ]:
                line.check_cost_centers_block = True
            else:
                line.check_cost_centers_block = False

    @api.onchange("account_id")
    def _onchange_account_id(self):
        for line in self:
            if line.account_id:
                # Reset analytics & partner when account changes
                line.analytic_distribution = False
                line.partner_id = False

    @api.onchange("cs_project_id")
    def _onchange_cs_project_id(self):
        for line in self:
            analytic_distribution = {}
            if line.cs_project_id:
                if line.cs_project_id.department_id:
                    analytic_distribution[
                        str(line.cs_project_id.department_id.id)
                    ] = 100.0
                if line.cs_project_id.section_id:
                    analytic_distribution[
                        str(line.cs_project_id.section_id.id)
                    ] = 100.0
                analytic_distribution[str(line.cs_project_id.id)] = 100.0

                if line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id

            line.analytic_distribution = analytic_distribution

    # endregion [Onchange / Compute]

    # region [Constraints]

    @api.constrains("debit", "credit")
    def _check_amounts(self):
        for line in self:
            if (line.debit <= 0.0 and line.credit <= 0.0) or (
                    line.debit and line.credit
            ):
                raise ValidationError(
                    _(
                        "Each line must have either a positive Debit "
                        "or a positive Credit (but not both)."
                    )
                )




    # endregion [Constraints]
