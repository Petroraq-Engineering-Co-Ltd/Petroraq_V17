from odoo import models, fields, api, _


class KsDynamicFinancialReportAccount(models.Model):
    _name = 'ks.dynamic.financial.reports.account'

    ks_name = fields.Char(string="Name")
    ks_account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."
    )

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