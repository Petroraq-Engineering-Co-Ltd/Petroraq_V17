from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    budget_type = fields.Selection([
        ('opex', 'Opex'),
        ('capex', 'Capex')
    ], string='Budget Type')

    budget_code = fields.Char(string='Cost Center Code')
    budget_allowance = fields.Float(string='Budget Allowance')
    all_bank_accounts = fields.Many2many(
        'res.partner.bank',
        string='Bank Accounts',
        default=lambda self: self.env['res.partner.bank'].search([])
    )
    budget_left = fields.Float(
        string="Budget Left",
        compute="_compute_budget_left",
        store=True
    )

    @api.depends('budget_allowance', 'purchase_order_ids.amount_total', 'purchase_order_ids.status')
    def _compute_budget_left(self):
        for project in self:
            approved_pos = project.purchase_order_ids.filtered(lambda po: po.status == 'approved')
            spent = sum(approved_po.amount_total for approved_po in approved_pos)
            project.budget_left = project.budget_allowance - spent

    purchase_order_ids = fields.One2many('purchase.order', 'project_id', string='Purchase Orders')