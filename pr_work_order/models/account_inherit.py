from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    work_order_id = fields.Many2one("pr.work.order", string="Work Order")

    @api.onchange("work_order_id")
    def _onchange_work_order_id(self):
        """
        When a Work Order is selected on the bill header:
        - Push WO to all invoice lines (for domain on cost centers)
        - Optionally set a default analytic account if WO has one
        """
        for move in self:
            for line in move.invoice_line_ids:
                # Clear cost center when WO changes
                line.wo_cost_center_id = False

                # If work order has a main analytic account and line has none,
                # use it as a default (you can comment this out if not needed)
                if (
                        move.work_order_id
                        and move.work_order_id.analytic_account_id
                        and not line.analytic_account_id
                ):
                    line.analytic_account_id = (
                        move.work_order_id.analytic_account_id.id
                    )


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    work_order_id = fields.Many2one(
        "pr.work.order",
        string="Work Order",
        help="Work Order this analytic entry belongs to.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            aml = line.move_line_id  # <-- CORRECT FIELD IN ODOO 17
            if aml and not line.work_order_id and aml.move_id.work_order_id:
                line.work_order_id = aml.move_id.work_order_id.id
        return lines


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    wo_cost_center_id = fields.Many2one(
        "pr.work.order.cost.center",
        string="WO Cost Center",
        domain="[('work_order_id', '=', parent.work_order_id)]",
    )

    @api.onchange("wo_cost_center_id")
    def _onchange_wo_cost_center_id(self):
        """
        When user selects a WO cost center on the bill line,
        automatically set analytic_account_id = cost center's analytic account.
        """
        for line in self:
            if line.wo_cost_center_id and line.wo_cost_center_id.analytic_account_id:
                line.analytic_distribution = (
                    line.wo_cost_center_id.analytic_account_id.id
                )
