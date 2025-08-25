from odoo import api, fields, models, _, Command
from odoo.tools import  float_compare
from odoo.exceptions import ValidationError


class AccountBankReceipt(models.Model):
    # region [Initial]
    _name = 'pr.account.bank.receipt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bank Receipt'
    _order = "id"
    _rec_name = 'name'
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string="Bank Receipt", required=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, required=True,
                                 default=lambda self: self.env.company,
                                 tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True,
                                  tracking=True)
    account_id = fields.Many2one('account.account', string='Acc. Code', required=True,
                                 ondelete='restrict', tracking=True, index=True,)
    account_name = fields.Char(string='Acc. Name', related="account_id.name", store=True,
                                     tracking=True)
    # === Analytic fields === #
    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='bank_receipt_id',
        string='Analytic lines',
    )
    analytic_distribution = fields.Json(
        string="Cost Centers",
        inverse="_inverse_analytic_distribution",
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    description = fields.Text(string="Description", required=False, tracking=True)
    accounting_date = fields.Date(string="Date", required=True, tracking=True, default=fields.Date.today)
    state = fields.Selection([
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("cancel", "Cancelled"),
    ], string="Status", tracking=True, default="draft")
    bank_receipt_line_ids = fields.One2many("pr.account.bank.receipt.line", "bank_receipt_id", string="Bank Receipt Lines")
    total_amount = fields.Float(string="Amount", compute="_compute_total_amount", store=True, tracking=True)
    journal_entry_id = fields.Many2one("account.move", string="Journal Entry", readonly=True, tracking=True)

    # endregion [Fields]

    # region [Constrains]

    @api.constrains("company_id")
    def _check_company(self):
        for bank_receipt in self:
            if bank_receipt.company_id and bank_receipt.company_id.id != self.env.company.id:
                raise ValidationError("You Should Select The Current Company !!, Please Check"
                                      "")

    # endregion [Constrains

    # region [Compute Methods]

    @api.depends("bank_receipt_line_ids", "bank_receipt_line_ids.total_amount")
    def _compute_total_amount(self):
        for bank_receipt in self:
            if bank_receipt.bank_receipt_line_ids:
                bank_receipt.total_amount = sum(bank_receipt.bank_receipt_line_ids.mapped("total_amount"))
            else:
                bank_receipt.total_amount = 0.0


    # endregion [Compute Methods]

    # region [Actions]

    def make_all_draft(self):
        bank_receipt_ids = self.env["pr.account.bank.receipt"].sudo().search([("id", "!=", False)])
        if bank_receipt_ids:
            for rec in bank_receipt_ids:
                rec.sudo().action_post()

    def action_draft(self):
        for bank_receipt in self:
            if bank_receipt.journal_entry_id and bank_receipt.journal_entry_id.state != "draft":
                bank_receipt.journal_entry_id.sudo().button_draft()
                bank_receipt.journal_entry_id.unlink()
            bank_receipt.state = "draft"


    def action_post(self):
        for bank_receipt in self:
            if bank_receipt.bank_receipt_line_ids:
                journal_entry_id = self.env['account.move'].create({
                    # 'name': bank_receipt.name,
                    'ref': bank_receipt.name,
                    'date': bank_receipt.accounting_date,
                    'move_type': 'entry',
                })
                if journal_entry_id:
                    journal_entry_id = journal_entry_id.with_context(check_move_validity=False)
                    move_line = self.env['account.move.line'].with_context(check_move_validity=False,
                                                                           skip_invoice_sync=True)
                    line_ids = [
                        move_line.create(bank_receipt.prepare_debit_move_line_vals(move_id=journal_entry_id))
                    ]
                    for line in bank_receipt.bank_receipt_line_ids:
                        line_ids.append(move_line.create(line.prepare_credit_move_line_vals(move_id=journal_entry_id)))
                        if line.tax_id:
                            line_ids.append(move_line.create(line.prepare_credit_tax_move_line_vals(move_id=journal_entry_id)))
                    journal_entry_id.action_post()
                    bank_receipt.journal_entry_id = journal_entry_id.id
            bank_receipt.state = "posted"

    def action_cancel(self):
        for bank_receipt in self:
            if bank_receipt.journal_entry_id and bank_receipt.journal_entry_id.state != "cancel":
                bank_receipt.journal_entry_id.sudo().button_draft()
                bank_receipt.journal_entry_id.sudo().button_cancel()
            bank_receipt.state = "cancel"

    def open_journal_entry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.journal_entry_id.id,
        }

    def prepare_debit_move_line_vals(self, move_id=False):
        for bank_receipt in self:
            line_vals = {
                "account_id": bank_receipt.account_id.id,
                "name": bank_receipt.description if bank_receipt.description else f"Debit For {bank_receipt.name}",
                "analytic_distribution": bank_receipt.analytic_distribution if bank_receipt.analytic_distribution else False,
                "debit": bank_receipt.total_amount,
                "credit": 0.0,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    # endregion [Actions]

    # region [Analytic Distribution Methods]

    def _inverse_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.account.bank.receipt'].browse([
            line.id for line in self if line.state == "posted"
        ])
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    def _create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        # self._validate_analytic_distribution()
        analytic_line_vals = []
        for bank_receipt in self:
            analytic_line_vals.extend(bank_receipt._prepare_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}
            for account_ids, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(float(distribution), account_ids,
                                                                       distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.total_amount * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.total_amount * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or self.description
        return {
            'name': default_name,
            'date': self.accounting_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.name,
            'bank_receipt_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Analytic Distribution Methods]

    # region [Crud]

    @api.model
    def create(self, vals):
        '''
        We Inherit Create Method To Pass Sequence Fo Field Name
        '''
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('pr.account.bank.receipt.seq.code') or ''
        return res

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("This Bank Receipt Should Be Draft To Can Delete !!")
        return super().unlink()

    # endregion [Crud]

class AccountBankReceiptLine(models.Model):
    # region [Initial]
    _name = 'pr.account.bank.receipt.line'
    _description = 'Bank Receipt Line'
    # endregion [Initial]

    # region [Fields]

    bank_receipt_id = fields.Many2one('pr.account.bank.receipt', 'Bank Receipt', required=True)
    company_id = fields.Many2one('res.company', string='Company', related="bank_receipt_id.company_id", store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related="bank_receipt_id.currency_id", store=True)
    cs_project_id = fields.Many2one("account.analytic.account", string="Project",
                                    domain="[('analytic_plan_type', '=', 'project')]", tracking=True)
    partner_id = fields.Many2one('res.partner', string='Project Manager', tracking=True)
    account_id = fields.Many2one('account.account', string='Acc. Code', required=True,
                                 ondelete='restrict', tracking=True, index=True)
    account_name = fields.Char(string='Acc. Name', related="account_id.name", store=True,
                               tracking=True)
    description = fields.Text(string="Description", required=False, tracking=True)
    reference_number = fields.Char(string="Reference Number", required=False)
    # === Analytic fields === #
    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='bank_receipt_line_id',
        string='Analytic lines',
    )
    analytic_distribution = fields.Json(
        string="Cost Centers",
        inverse="_inverse_analytic_distribution",
    )
    analytic_precision = fields.Integer(
        related="bank_receipt_id.analytic_precision",
        store=False,
    )
    amount = fields.Float(string="Amount", tracking=True)
    tax_id = fields.Many2one('account.tax', string='Taxes', ondelete='restrict', check_company=True, domain="[('type_tax_use', '=', 'sale')]")
    amount_tax = fields.Float(string="Tax Amount", tracking=True, compute="_compute_amount", store=True)
    total_amount = fields.Float(string="Total Amount", tracking=True, compute="_compute_amount", store=True)
    parent_state = fields.Selection([
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("cancel", "Cancelled"),
    ], related="bank_receipt_id.state", store=True, string="Parent Status")
    check_cost_centers_block = fields.Boolean(compute="_compute_check_cost_centers_block")
    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("account_id")
    def _onchange_account_id(self):
        for line in self:
            if line.account_id:
                line.analytic_distribution = False
                line.partner_id = False

    @api.onchange("cs_project_id")
    def _onchange_cs_project_id(self):
        for line in self:
            project_ids = self.env["account.analytic.account"].sudo().search(
                [("analytic_plan_type", "=", "project")]).mapped("id")

            analytic_distribution = {}
            if line.cs_project_id:
                # Analytic Distribution
                if line.cs_project_id.department_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.department_id.id): 100.0
                    })
                if line.cs_project_id.section_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.section_id.id): 100.0
                    })
                analytic_distribution.update({
                    str(line.cs_project_id.id): 100.0
                })

                # Project Manager
                if line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id
            line.analytic_distribution = analytic_distribution
            # Analytic Distribution

    # endregion [Onchange Methods]

    # region [Constrains]

    @api.constrains("amount")
    def _check_amount(self):
        for bank_receipt_line in self:
            if bank_receipt_line.amount <= 0:
                raise ValidationError("Amount Must Be Greater Than 0 ( Zero ) !!")

    # endregion [Constrains]

    # region [Compute Methods]

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=False,
            currency=self.currency_id,
            product=False,
            taxes=self.tax_id,
            price_unit=self.amount,
            quantity=1,
            discount=0,
            price_subtotal=self.amount,
        )

    @api.depends('amount', 'tax_id', 'currency_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for bank_receipt_line in self:
            if bank_receipt_line.tax_id and bank_receipt_line.currency_id:
                tax_results = self.env['account.tax']._compute_taxes([
                    bank_receipt_line._convert_to_tax_base_line_dict()
                ])
                totals = list(tax_results['totals'].values())[0]
                amount_untaxed = totals['amount_untaxed']
                amount_tax = totals['amount_tax']

                bank_receipt_line.update({
                    'amount_tax': amount_tax,
                    'total_amount': amount_untaxed + amount_tax,
                })
            else:
                bank_receipt_line.amount_tax = 0.0
                bank_receipt_line.total_amount = bank_receipt_line.amount

    # @api.depends("account_id", "account_id.cash_equivalents_subcategory", "account_id.accounts_receivable_subcategory")
    # @api.onchange("account_id", "account_id.cash_equivalents_subcategory", "account_id.accounts_receivable_subcategory")
    @api.depends("account_id", "account_id.main_head")
    @api.onchange("account_id", "account_id.main_head")
    def _compute_check_cost_centers_block(self):
        for line in self:
            if line.account_id and line.account_id.main_head in ["revenue", "expense"]:
                line.check_cost_centers_block = True
            else:
                line.check_cost_centers_block = False

    # endregion [Compute Methods]

    # region [Move Line Vals]

    def prepare_credit_move_line_vals(self, move_id=False):
        for bank_receipt_line in self:
            line_vals = {
                "account_id": bank_receipt_line.account_id.id,
                "partner_id": bank_receipt_line.partner_id.id if bank_receipt_line.partner_id else False,
                "name": bank_receipt_line.description if bank_receipt_line.description else f"Credit Line For {bank_receipt_line.bank_receipt_id.name}",
                "analytic_distribution": bank_receipt_line.analytic_distribution if bank_receipt_line.analytic_distribution else False,
                "cs_project_id": bank_receipt_line.cs_project_id.id if bank_receipt_line.cs_project_id else False,
                "credit": bank_receipt_line.amount if bank_receipt_line.tax_id else bank_receipt_line.total_amount,
                'tax_ids': bank_receipt_line.tax_id.ids if bank_receipt_line.tax_id else False,
                "debit": 0.0,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    def prepare_credit_tax_move_line_vals(self, move_id=False):
        for bank_receipt_line in self:
            default_account_tax_id = bank_receipt_line.tax_id.mapped('invoice_repartition_line_ids.account_id')
            repartition_tax_line = bank_receipt_line.tax_id.invoice_repartition_line_ids.filtered(
                lambda l: l.repartition_type == 'tax' and l.account_id)
            if not default_account_tax_id or not repartition_tax_line:
                raise ValidationError(f"Please Set Account In The {bank_receipt_line.tax_id.name}")
            line_vals = {
                "account_id": default_account_tax_id.id,
                "partner_id": bank_receipt_line.partner_id.id if bank_receipt_line.partner_id else False,
                "name": bank_receipt_line.description if bank_receipt_line.description else f"Credit Tax Line For {bank_receipt_line.bank_receipt_id.name}",
                "analytic_distribution": bank_receipt_line.analytic_distribution if bank_receipt_line.analytic_distribution else False,
                "cs_project_id": bank_receipt_line.cs_project_id.id if bank_receipt_line.cs_project_id else False,
                'display_type': 'tax',
                'tax_repartition_line_id': repartition_tax_line.id,
                'tax_line_id': bank_receipt_line.tax_id.id,
                "credit": bank_receipt_line.amount_tax,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    # endregion [Move Line Vals]

    # region [Analytic Distribution Methods]

    def _inverse_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.account.bank.receipt.line'].browse([
            line.id for line in self if line.parent_state == "posted"
        ])
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    def _create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        # self._validate_analytic_distribution()
        analytic_line_vals = []
        for bank_receipt_line in self:
            analytic_line_vals.extend(bank_receipt_line._prepare_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}
            for account_ids, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(float(distribution), account_ids,
                                                                             distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.total_amount * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.total_amount * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.description
        return {
            'name': default_name,
            'date': self.bank_receipt_id.accounting_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.bank_receipt_id.name,
            'bank_receipt_line_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Analytic Distribution Methods]

