from odoo import api, fields, models, _


class HrEmployee(models.Model):
    # region [Initial]
    _inherit = 'hr.employee'
    # endregion [Initial]

    employee_cost_center_id = fields.Many2one("account.analytic.account", string="Employee Cost Center",
                                    domain="[('analytic_plan_type', '=', 'employee')]")
    employee_account_id = fields.Many2one("account.account", string="Employee Account")


