from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = "project.project"

    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type"
    )
    budget_code = fields.Char(string="Cost Center Code")
    budget_allowance = fields.Float(string="Budget Allowance")
    all_bank_accounts = fields.Many2many(
        "res.partner.bank",
        string="Bank Accounts",
        default=lambda self: self.env["res.partner.bank"].search([]),
    )
    budget_left = fields.Float(
        string="Budget Left", compute="_compute_budget_left", store=True
    )
    purchase_order_ids = fields.One2many(
        'purchase.order', 'project_id', string='Purchase Orders'
    )

    @api.depends(
        "budget_allowance",
        "purchase_order_ids.amount_total",
        "purchase_order_ids.pe_approved",   
        "purchase_order_ids.pm_approved",
        "purchase_order_ids.od_approved",
        "purchase_order_ids.md_approved",
        "purchase_order_ids.state",   
    )
    def _compute_budget_left(self):
        for project in self:
            spent = 0
            for po in project.purchase_order_ids:
                approvals_needed = 0
                approvals_given = 0

                # Determine how many approvals are needed based on amount
                if po.amount_total < 10000:
                    approvals_needed = 1
                    approvals_given = 1 if po.pe_approved else 0
                elif po.amount_total < 100000:
                    approvals_needed = 2
                    approvals_given = sum([po.pe_approved, po.pm_approved])
                elif po.amount_total < 500000:
                    approvals_needed = 3
                    approvals_given = sum([po.pe_approved, po.pm_approved, po.od_approved])
                else:
                    approvals_needed = 4
                    approvals_given = sum([po.pe_approved, po.pm_approved, po.od_approved, po.md_approved])

                # Add to spent only if all required approvals are given
                if approvals_given >= approvals_needed and po.state != 'cancel':
                    spent += po.amount_total

                # If rejected (state = cancel), do NOT add — budget remains restored automatically

            project.budget_left = project.budget_allowance - spent

