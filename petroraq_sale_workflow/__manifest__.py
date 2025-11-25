{
    "name": "Petroraq: Sales Workflow",
    "summary": "Inquiry → Quotation → Manager Approval → MD Approval → Send to Client",
    "version": "17.0.1.0.0",
    "author": "Petroraq Engineering & Construction Co. Ltd.",
    "website": "https://petroraq.com",
    "category": "Sales",
    "license": "OEEL-1",
    "depends": ["sale", "mail", "account"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/payment_terms.xml",
        "data/sequence.xml",
        "views/sale_order_views.xml",
        "views/inquiry_views.xml",
        "views/company_views.xml",   # new: company form settings (v17-safe)
        "views/reject_wizard_views.xml",
        "data/mail_template.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "petroraq_sale_workflow/static/src/scss/section_subtotals.scss",
            "petroraq_sale_workflow/static/src/xml/section_subtotals.xml",
        ],
    },
    "post_init_hook": "petroraq_sale_workflow_create_payment_terms",
    "application": False,
    "installable": True,
}
