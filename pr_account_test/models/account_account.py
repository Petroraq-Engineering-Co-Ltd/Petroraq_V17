from odoo import api, fields, models, _

MAIN_HEAD_FIELDS = ["assets_main_head", "liability_main_head"]
CATEGORY_FIELDS = ["current_assets_category", "fixed_assets_category", "other_assets_category", "current_liability_category", "liability_non_current_category", "equity_category", "revenue_category", "expense_category"]
CURRENT_ASSET_FIELDS = ["cash_equivalents_subcategory", "banks_subcategory", "accounts_receivable_subcategory", "inventory_subcategory", "prepaid_expenses_subcategory"]
FIXED_ASSET_FIELDS = ["vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory", "machinery_equipment_subcategory", "land_buildings_subcategory"]
OTHER_ASSET_FIELDS = ["investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory"]

CURRENT_LIABILITY_FIELDS = ["accounts_payable_subcategory", "short_term_loans_subcategory", "other_liabilities_subcategory"]
NON_CURRENT_LIABILITY_FIELDS = ["long_term_loans_subcategory", "lease_obligations_subcategory"]

EQUITY_FIELDS = ["capital_subcategory"]

REVENUE_FIELDS = ["operating_revenue_subcategory"]

EXPENSE_FIELDS = ["cogs_subcategory", "operating_expenses_subcategory", "financial_expenses_subcategory", "other_expenses_subcategory"]


class AccountAccount(models.Model):
    # region [Initial]
    _inherit = 'account.account'
    # endregion [Initial]

    # region [Fields]

    main_head = fields.Selection([
        ("assets", "Assets"),
        ("liabilities", "Liabilities"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ], string="Main Head", required=False, tracking=True)
    assets_main_head = fields.Selection([
        ("asset_current", "Current Assets"),
        ("asset_fixed", "Fixed Assets"),
        ("asset_non_current", "Other Assets"),
    ], string="Assets Main Head", tracking=True)
    liability_main_head = fields.Selection([
        ("liability_current", "Current Liabilities"),
        ("liability_non_current", "Long-Term Liabilities"),
    ], string="Liabilities Main Head", tracking=True)
    # -- Category -- #
    current_assets_category = fields.Selection([
        ("cash_equivalents", "Cash & Equivalents"),
        ("banks", "Banks"),
        ("account_receivable", "Account Receivable"),
        ("inventory", "Inventory"),
        ("prepaid_expenses", "Prepaid Expenses"),
    ], string="Current Assets Category", tracking=True)
    fixed_assets_category = fields.Selection([
        ("vehicles", "Vehicles"),
        ("furniture_fixture", "Furniture & Fixture"),
        ("computer_printers", "Computer & Printers"),
        ("machinery_equipment", "Machinery & Equipment"),
        ("land_buildings", "Land & Buildings"),
    ], string="Fixed Assets Category", tracking=True)
    other_assets_category = fields.Selection([
        ("investment", "Investment"),
        ("vat_receivable", "VAT Receivable"),
        ("suspense_account", "Suspense Account"),
    ], string="Other Assets Category", tracking=True)
    current_liability_category = fields.Selection([
        ("accounts_payable", "Accounts Payable"),
        ("short_term_loans", "Short-Term Loans"),
        ("other_liabilities", "Other Liabilities"),
    ], string="Current Liabilities Category", tracking=True)
    liability_non_current_category = fields.Selection([
        ("long_term_loans", "Long-Term Loans"),
        ("lease_obligations", "Lease Obligations"),
    ], string="Non Current Liabilities Category", tracking=True)
    equity_category = fields.Selection([
        ("capital", "Capital"),
    ], string="Equity Category", tracking=True)
    revenue_category = fields.Selection([
        ("operating_revenue", "Operating Revenue"),
    ], string="Revenue Category", tracking=True)
    expense_category = fields.Selection([
        ("cogs", "Cost of Goods Sold - COGS"),
        ("operating_expenses", "Operating Expenses"),
        ("financial_expenses", "Financial Expenses"),
        ("other_expenses", "Other Expenses"),
    ], string="Expense Category", tracking=True)
    # -- Sub Category -- #
    cash_equivalents_subcategory = fields.Selection([
        ("petty_cash", "Petty Cash"),
    ], string="Cash & Equivalents Sub-Category", tracking=True)
    banks_subcategory = fields.Selection([
        ("banks", "Banks"),
    ], string="Banks Sub-Category", tracking=True)
    accounts_receivable_subcategory = fields.Selection([
        ("employee_advances", "Employee Advances"),
        ("customers", "Customers"),
        ("retention_receivable", "Retention-Receivable"),
    ], string="Accounts Receivable Sub-Category", tracking=True)
    inventory_subcategory = fields.Selection([
        ("raw_materials", "Raw Materials"),
        ("work_in_progress_wip", "Work in Progress-WIP"),
        ("finished_goods", "Finished Goods"),
    ], string="Inventory Sub-Category", tracking=True)
    prepaid_expenses_subcategory = fields.Selection([
        ("prepaid_rent", "Prepaid Rent"),
        ("insurance", "Insurance"),
        ("subscriptions", "Subscriptions"),
    ], string="Prepaid Expenses Sub-Category", tracking=True)
    vehicles_subcategory = fields.Selection([
        ("cars", "Cars"),
    ], string="vehicles Sub-Category", tracking=True)
    furniture_fixture_subcategory = fields.Selection([
        ("furniture", "Furniture"),
    ], string="Furniture & Fixture Sub-Category", tracking=True)
    computer_printers_subcategory = fields.Selection([
        ("it_products", "IT Products"),
    ], string="Computer & Printers Sub-Category", tracking=True)
    machinery_equipment_subcategory = fields.Selection([
        ("machinery", "Machinery"),
    ], string="Machinery & Equipment Sub-Category", tracking=True)
    land_buildings_subcategory = fields.Selection([
        ("buildings", "Buildings"),
    ], string="Land & Buildings Sub-Category", tracking=True)
    investment_subcategory = fields.Selection([
        ("short_terms", "Short Terms"),
        ("long_terms", "Long Terms"),
    ], string="Investment Sub-Category", tracking=True)
    vat_receivable_subcategory = fields.Selection([
        ("vat_receivable", "VAT Receivable"),
    ], string="VAT Receivable Sub-Category", tracking=True)
    suspense_account_subcategory = fields.Selection([
        ("suspense_account", "Suspense Account"),
    ], string="Suspense Account Sub-Category", tracking=True)
    accounts_payable_subcategory = fields.Selection([
        ("suppliers", "Suppliers"),
        ("accrued_expenses", "Accrued Expenses"),
        ("bank", "Bank"),
    ], string="Accounts Payable Sub-Category", tracking=True)
    short_term_loans_subcategory = fields.Selection([
        ("bank_finance", "Bank Finance"),
    ], string="Short Term Loans Sub-Category", tracking=True)
    other_liabilities_subcategory = fields.Selection([
        ("vat_payable", "VAT Payable"),
    ], string="Other Liabilities Sub-Category", tracking=True)
    long_term_loans_subcategory = fields.Selection([
        ("loans", "Loans"),
    ], string="Long Term Loans Sub-Category", tracking=True)
    lease_obligations_subcategory = fields.Selection([
        ("lease", "Lease"),
    ], string="Lease Obligations Sub-Category", tracking=True)
    capital_subcategory = fields.Selection([
        ("petroraq", "Petroraq"),
    ], string="Capital Sub-Category", tracking=True)
    operating_revenue_subcategory = fields.Selection([
        ("product_sales", "Product Sales"),
        ("service_revenue", "Service Revenue"),
        ("other_revenue", "Other Revenue"),
    ], string="Operating Revenue Sub-Category", tracking=True)
    cogs_subcategory = fields.Selection([
        ("direct_raw_materials", "Direct Raw Materials"),
        ("direct_labor", "Direct Labor (Production Staff)"),
    ], string="COGS Sub-Category", tracking=True)
    operating_expenses_subcategory = fields.Selection([
        ("salaries_wages", "Salaries & Wages"),
        ("rent_utilities", "Rent & Utilities"),
        ("marketing", "Marketing"),
    ], string="operating_expenses Sub-Category", tracking=True)
    financial_expenses_subcategory = fields.Selection([
        ("interest_expense", "Interest Expense"),
    ], string="Financial Expenses Sub-Category", tracking=True)
    other_expenses_subcategory = fields.Selection([
        ("general_administrative_expenses", "General Administrative Expenses"),
    ], string="Other Expenses Sub-Category", tracking=True)

    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("main_head")
    def _onchange_main_head(self):
        ALL_FIELD_GROUPS = (
                MAIN_HEAD_FIELDS +
                CATEGORY_FIELDS +
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for account in self:
            if account.main_head:
                for field in ALL_FIELD_GROUPS:
                    setattr(account, field, False)

    @api.onchange("assets_main_head", "liability_main_head")
    def _onchange_assets_liability_main_head(self):
        ALL_FIELD_GROUPS = (
                CATEGORY_FIELDS +
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for account in self:
            if account.assets_main_head or account.liability_main_head:
                for field in ALL_FIELD_GROUPS:
                    setattr(account, field, False)

    @api.onchange("current_assets_category", "fixed_assets_category", "other_assets_category", "current_liability_category", "liability_non_current_category", "equity_category", "revenue_category", "expense_category")
    def _onchange_category(self):
        ALL_FIELD_GROUPS = (
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for account in self:
            if (account.assets_main_head or account.liability_main_head or account.current_assets_category or account.fixed_assets_category \
                    or account.other_assets_category or account.current_liability_category or account.liability_non_current_category or account.equity_category
                    or account.revenue_category or account.expense_category):
                for field in ALL_FIELD_GROUPS:
                    setattr(account, field, False)

    # endregion [Onchange Methods]

    # region [System Methods]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for account in self:
            # account.display_name = f"{account.code} : {account.name}"
            account.display_name = f"{account.code}"

    # region [System Methods]

