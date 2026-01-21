# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, date
import json
from collections import defaultdict
from odoo.tools import float_round

MAIN_HEAD = ["main_head"]
MAIN_HEAD_FIELDS = ["assets_main_head", "liability_main_head"]
CATEGORY_FIELDS = ["current_assets_category", "fixed_assets_category", "other_assets_category",
                   "current_liability_category", "liability_non_current_category", "equity_category",
                   "revenue_category", "expense_category"]
CURRENT_ASSET_FIELDS = ["cash_equivalents_subcategory", "banks_subcategory", "accounts_receivable_subcategory",
                        "inventory_subcategory", "prepaid_expenses_subcategory"]
FIXED_ASSET_FIELDS = ["vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory",
                      "machinery_equipment_subcategory", "land_buildings_subcategory"]
OTHER_ASSET_FIELDS = ["investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory"]

CURRENT_LIABILITY_FIELDS = ["accounts_payable_subcategory", "short_term_loans_subcategory",
                            "other_liabilities_subcategory"]
NON_CURRENT_LIABILITY_FIELDS = ["long_term_loans_subcategory", "lease_obligations_subcategory"]

EQUITY_FIELDS = ["capital_subcategory"]

REVENUE_FIELDS = ["operating_revenue_subcategory"]

EXPENSE_FIELDS = ["cogs_subcategory", "operating_expenses_subcategory", "financial_expenses_subcategory",
                  "other_expenses_subcategory"]


class CustomDynamicLedgerReportWizard(models.TransientModel):
    _name = 'custom.dynamic.ledger.report.wizard'

    # region [Default Methods]

    # endregion [Default Methods]

    date_start = fields.Date(string="Start Date", required=True, default=date(2025, 1, 1))
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)
    # region [Account Filter Fields]

    main_head = fields.Selection([
        ("assets", "Assets"),
        ("liabilities", "Liabilities"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ], string="Report Type", required=True, tracking=True)

    # endregion [Account Filter Fields]
    account_id = fields.Many2one('account.account', required=False, string="Account",
                                 domain="[('main_head', '=', main_head)]")
    account_id_domain = fields.Char(compute="_compute_account_id_domain")
    account_name = fields.Char(string='Account Name', related="account_id.name")
    company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company)
    department_id = fields.Many2one('account.analytic.account', string="Department",
                                    domain="[('analytic_plan_type', '=', 'department')]")
    section_id = fields.Many2one('account.analytic.account', string="Section",
                                 domain="[('analytic_plan_type', '=', 'section')]")
    project_id = fields.Many2one('account.analytic.account', string="Project",
                                 domain="[('analytic_plan_type', '=', 'project')]")

    def _get_analytic_domain(self):
        analytic_domain = []
        analytic_ids = []

        if self.department_id:
            analytic_ids.append(self.department_id.id)
        if self.section_id:
            analytic_ids.append(self.section_id.id)
        if self.project_id:
            analytic_ids.append(self.project_id.id)

        for analytic_id in analytic_ids:
            analytic_domain.append(('analytic_distribution', 'has_key', str(analytic_id)))

        return analytic_domain

    @api.depends("date_start", "date_end")
    def _compute_account_id_domain(self):
        for rec in self:
            if self.env.user.has_group('account.group_account_manager') or self.env.user.has_group(
                    'pr_account.custom_group_accounting_manager'):
                rec.account_id_domain = "[]"
            else:
                rec.account_id_domain = "[('id', '!=', 749)]"

    # def _prepare_initial_balance_domain(self):
    #     for rec in self:
    #         analytic_distribution_ids = []
    #         domain = [
    #             ("account_id.main_head", "=", rec.main_head),
    #             ("company_id", "=", rec.company_id.id),
    #             ('date', '<', rec.date_start),
    #             ('parent_state', '=', "posted")
    #         ]
    #         if rec.account_id:
    #             domain.append(("account_id", "=", rec.account_id.id))
    #         if rec.department_id:
    #             analytic_distribution_ids.append(int(rec.department_id.id))
    #         if rec.section_id:
    #             analytic_distribution_ids.append(int(rec.section_id.id))
    #         if rec.project_id:
    #             analytic_distribution_ids.append(int(rec.project_id.id))
    #         if analytic_distribution_ids:
    #             domain.append(('analytic_distribution', 'in', analytic_distribution_ids))
    #         return domain
    #     return None
    #
    # def _prepare_ji_domain(self):
    #     for rec in self:
    #         analytic_distribution_ids = []
    #         domain = [
    #             ("account_id.main_head", "=", rec.main_head),
    #             ("company_id", "=", rec.company_id.id),
    #             ('date', '>=', rec.date_start),
    #             ('date', '<=', rec.date_end),
    #             ('parent_state', '=', "posted")
    #         ]
    #         if rec.account_id:
    #             domain.append(("account_id", "=", rec.account_id.id))
    #         if rec.department_id:
    #             analytic_distribution_ids.append(int(rec.department_id.id))
    #         if rec.section_id:
    #             analytic_distribution_ids.append(int(rec.section_id.id))
    #         if rec.project_id:
    #             analytic_distribution_ids.append(int(rec.project_id.id))
    #         if analytic_distribution_ids:
    #             domain.append(('analytic_distribution', 'in', analytic_distribution_ids))
    #         return domain
    #     return None
    #
    #
    # def get_report(self):
    #     ji_domain = self._prepare_hi_domain()
    #     data = {
    #         'ids': self.ids,
    #         'model': self._name,
    #         'form': {
    #             'date_start': self.date_start,
    #             'date_end': self.date_end,
    #             'account': self.account_ids.ids,
    #             'company': self.company_id.id,
    #             'vat_option': self.vat_option,
    #             'department': self.department_id.id if self.department_id else False,
    #             'section': self.section_id.id if self.section_id else False,
    #             'project': self.project_id.id if self.project_id else False,
    #             'employee': self.employee_id.id if self.employee_id else False,
    #             'asset': self.asset_id.id if self.asset_id else False,
    #         },
    #     }
    #     return self.env.ref('account_ledger.vat_leg_report').report_action(self, data=data)

    def print_report(self):
        """Call when button 'Get Report' clicked.
        """
        return self.print_xlsx_report()

    def print_xlsx_report(self):
        """Call when button 'Get Report' clicked.
        """

        return self.env.ref('account_ledger.custom_dynamic_ledger_report_view_xlsx').report_action(self, data=None)

    def get_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'main_head': self.main_head,
                'company': self.company_id.id,
                'department': self.department_id.id if self.department_id else False,
                'section': self.section_id.id if self.section_id else False,
                'project': self.project_id.id if self.project_id else False,
            },
        }
        return self.env.ref('account_ledger.custom_dynamic_ledger_report_pdf').report_action(self, data=data)

    def action_view_custom_dynamic_ledger_report(self):
        self.ensure_one()

        report_rows = self.generate_balance_report()

        result = self.env["custom.dynamic.ledger.result"].create({
            "wizard_id": self.id
        })

        for row in report_rows:
            ending_debit = row['ending_debit']
            ending_credit = row['ending_credit']

            if ending_debit > ending_credit:
                balance = ending_debit - ending_credit
                balance_type = "Debit"
            elif ending_credit > ending_debit:
                balance = ending_credit - ending_debit
                balance_type = "Credit"
            else:
                balance = 0.0
                balance_type = "-"

            self.env["custom.dynamic.ledger.result.line"].create({
                "result_id": result.id,
                "label": row['level'],
                "initial_debit": row['initial_debit'],
                "initial_credit": row['initial_credit'],
                "period_debit": row['period_debit'],
                "period_credit": row['period_credit'],
                "ending_debit": ending_debit,
                "ending_credit": ending_credit,
                "balance": balance,
                "balance_type": balance_type,
            })

        return {
            "type": "ir.actions.act_window",
            "name": "Dynamic Balance Report",
            "res_model": "custom.dynamic.ledger.result",
            "res_id": result.id,
            "view_mode": "form",
            "target": "current",
        }

    def generate_balance_report(self):
        """
        Generate a hierarchical trial balance report:
        - Grouped by: Main Head → Category → Subcategory → Account
        - Output: List of rows for Excel/table
        """
        domain = [
            ("main_head", "=", self.main_head),
            ("main_head", "!=", False),
            ("company_id", "in", [self.company_id.id, self.company_id.parent_id.id]),
        ]
        if self.account_id:
            domain.append(("id", "=", self.account_id.id))

        accounts = self.env['account.account'].sudo().search(domain)

        grouped_data = defaultdict(lambda: {
            'summary': self.init_balance_totals(),
            'categories': defaultdict(lambda: {
                'summary': self.init_balance_totals(),
                'subcategories': defaultdict(lambda: {
                    'summary': self.init_balance_totals(),
                    'accounts': {}
                })
            })
        })

        for account in accounts:
            main_head = account.main_head
            category = self.get_category(account)
            subcategory = self.get_subcategory(account)

            initial = self.compute_balance(account.id, self.company_id, start_date=self.date_start,
                                           end_date=self.date_end, before=True)
            period = self.compute_balance(account.id, self.company_id, start_date=self.date_start,
                                          end_date=self.date_end)

            # ending = {
            #     'debit': initial['debit'] + period['debit'],
            #     'credit': initial['credit'] + period['credit'],
            # }

            ending = {
                'debit': period['debit'],
                'credit': period['credit'],
            }

            account_key = f"{account.code} - {account.name}"
            # account_row = {
            #     'initial_debit': initial['debit'],
            #     'initial_credit': initial['credit'],
            #     'period_debit': period['debit'],
            #     'period_credit': period['credit'],
            #     'ending_debit': ending['debit'],
            #     'ending_credit': ending['credit'],
            # }
            account_row = {
                'initial_debit': 0,
                'initial_credit': 0,
                'period_debit': period['debit'],
                'period_credit': period['credit'],
                'ending_debit': ending['debit'],
                'ending_credit': ending['credit'],
            }

            subcat_data = grouped_data[main_head]['categories'][category]['subcategories'][subcategory]
            subcat_data['accounts'][account_key] = account_row

            self.update_totals(grouped_data[main_head]['summary'], account_row)
            self.update_totals(grouped_data[main_head]['categories'][category]['summary'], account_row)
            self.update_totals(subcat_data['summary'], account_row)

        report_rows = []

        for main_head, main_data in grouped_data.items():
            report_rows.append(self.format_row(main_head.title(), main_data['summary'], level=0))  # ✅ return dict

            for category, cat_data in main_data['categories'].items():
                report_rows.append(self.format_row(category.title(), cat_data['summary'], level=1))  # ✅ return dict

                for subcategory, subcat_data in cat_data['subcategories'].items():
                    report_rows.append(self.format_row(subcategory.title(), subcat_data['summary'], level=2))  # ✅

                    for acc_label, acc_data in subcat_data['accounts'].items():
                        report_rows.append(self.format_row(acc_label, acc_data, level=3))  # ✅

        return report_rows

    def init_balance_totals(self):
        """
        Return a fresh dict for balance tracking.
        """
        return {
            'initial_debit': 0.0,
            'initial_credit': 0.0,
            'period_debit': 0.0,
            'period_credit': 0.0,
            'ending_debit': 0.0,
            'ending_credit': 0.0,
        }

    def update_totals(self, summary, data):
        """
        Add balance data into the summary totals.
        """
        for key in summary:
            summary[key] += float_round(data.get(key, 0.0), precision_digits=2)

    # def compute_balance(self, account_id, company_id, start_date=None, end_date=None, before=False):
    #     """
    #     Compute debit and credit totals for a given account.
    #     """
    #     analytic_distribution_ids = []
    #     domain = [
    #         ('account_id', '=', account_id),
    #         ('company_id', '=', company_id.id),
    #         ('move_id.state', '=', 'posted')
    #         # ('parent_state', '=', "posted")
    #     ]
    #     if before:
    #         domain.append(('date', '<', start_date))
    #     else:
    #         if start_date:
    #             domain.append(('date', '>=', start_date))
    #         if end_date:
    #             domain.append(('date', '<=', end_date))
    #
    #     if self.department_id:
    #         analytic_distribution_ids.append(int(self.department_id.id))
    #     if self.section_id:
    #         analytic_distribution_ids.append(int(self.section_id.id))
    #     if self.project_id:
    #         analytic_distribution_ids.append(int(self.project_id.id))
    #     if analytic_distribution_ids:
    #         domain.append(('analytic_distribution', 'in', analytic_distribution_ids))
    #
    #     result = self.env['account.move.line'].sudo().read_group(domain, ['debit', 'credit'], [])
    #
    #
    #     return {
    #         'debit': float_round(result[0]['debit'], 2) if result else 0.0,
    #         'credit': float_round(result[0]['credit'], 2) if result else 0.0,
    #     }

    def compute_balance(self, account_id, company_id, start_date=None, end_date=None, before=False):
        """
        Compute total debit and credit for the given account and period.
        If 'before' is True, include Opening Journal Entry amounts in the totals.
        """

        # Standard domain
        domain = [
            ('account_id', '=', account_id),
            ('company_id', '=', company_id.id),
            ('move_id.state', '=', 'posted'),
        ]

        if before:
            domain.append(('date', '<', start_date))
        else:
            if start_date:
                domain.append(('date', '>=', start_date))
            if end_date:
                domain.append(('date', '<=', end_date))

        # Add analytic filters if available

        # if self.department_id:
        #     analytic_distribution_ids.append(int(self.department_id.id))
        # if self.section_id:
        #     analytic_distribution_ids.append(int(self.section_id.id))
        # if self.project_id:
        #     analytic_distribution_ids.append(int(self.project_id.id))
        # if analytic_distribution_ids:
        #     domain.append(('analytic_distribution', 'in', analytic_distribution_ids))

        # Compute main result
        # result = self.env['account.move.line'].sudo().read_group(domain, ['debit', 'credit'], [])
        # debit = float_round(result[0].get('debit', 0.0), 2) if result else 0.0
        # credit = float_round(result[0].get('credit', 0.0), 2) if result else 0.0
        domain += self._get_analytic_domain()
        account_move_line_result = self.env['account.move.line'].sudo().search(domain, order="date asc")

        debit = float_round(sum(account_move_line_result.mapped("debit")), 2)
        credit = float_round(sum(account_move_line_result.mapped("credit")), 2)

        # Add OJE only if 'before' is True
        if before and start_date:
            oje_company_ids = [company_id.id]
            if company_id.parent_id:
                oje_company_ids.append(company_id.parent_id.id)

            oje_domain = [
                ('account_id', '=', account_id),
                ('company_id', 'in', oje_company_ids),
                ('date', '<', start_date),
                ('move_id.ref', '=', 'Opening Journal Entry'),
            ]
            oje_domain += self._get_analytic_domain()
            oje_result = self.env['account.move.line'].sudo().read_group(oje_domain, ['debit', 'credit'], [])
            if oje_result:
                debit += float_round(oje_result[0].get('debit', 0.0), 2)
                credit += float_round(oje_result[0].get('credit', 0.0), 2)

        return {
            'debit': debit,
            'credit': credit,
        }

    def format_row(self, label, data, level=0):
        """
        Format one row of the trial balance report.
        Indent the label by hierarchy level.
        """
        indent = "    " * level
        return {
            'level': f"{indent}{label}",
            'initial_debit': data['initial_debit'],
            'initial_credit': data['initial_credit'],
            'period_debit': data['period_debit'],
            'period_credit': data['period_credit'],
            'ending_debit': data['ending_debit'],
            'ending_credit': data['ending_credit'],
        }

    def get_category(self, account):
        if account.main_head == "assets":
            return getattr(account, "current_assets_category") or \
                getattr(account, "fixed_assets_category") or \
                getattr(account, "other_assets_category") or "Unclassified"
        elif account.main_head == "liabilities":
            return getattr(account, "current_liability_category") or \
                getattr(account, "liability_non_current_category") or "Unclassified"
        elif account.main_head == "equity":
            return getattr(account, "equity_category") or "Unclassified"
        elif account.main_head == "revenue":
            return getattr(account, "revenue_category") or "Unclassified"
        elif account.main_head == "expense":
            return getattr(account, "expense_category") or "Unclassified"
        return "Unclassified"

    def get_subcategory(self, account):
        category = self.get_category(account)
        if not category or category == 'Unclassified':
            return 'Unclassified'

        subcategory_fields = (
                CURRENT_ASSET_FIELDS + FIXED_ASSET_FIELDS + OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS + NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS + REVENUE_FIELDS + EXPENSE_FIELDS
        )

        for field in subcategory_fields:
            if getattr(account, field, False):
                return getattr(account, field)
        return 'Unclassified'
