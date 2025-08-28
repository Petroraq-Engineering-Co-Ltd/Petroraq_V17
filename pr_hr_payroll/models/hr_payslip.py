
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    other_amount = fields.Float(string="Other Amount", default=0.0)
    salary_journal_entry_id = fields.Many2one("account.move", readonly=True)

    def _get_payslip_lines(self):
        line_vals = super()._get_payslip_lines()
        for payslip in self:
            contract_id = payslip.employee_id.contract_id
            gosi_salary_rule = self.env.ref("pr_hr_payroll.hr_salary_rule_saudi_gosi")
            gosi_allow_salary_rule = self.env.ref("pr_hr_payroll.hr_salary_rule_saudi_gosi_allow")
            if payslip.employee_id.country_id and payslip.employee_id.country_id.is_homeland and contract_id.is_automatic_gosi:
                start_of_month = date_utils.start_of(payslip.date_to, 'month')
                end_of_month = date_utils.end_of(payslip.date_to, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                total_amount = 0
                if end_of_month > contract_id.date_start > payslip.date_from:
                    wage = contract_id.wage
                    salary_month_days = (end_of_month - contract_id.date_start).days + 1
                    total_amount = (salary_month_days * wage) / month_days
                elif payslip.date_from >= contract_id.date_start:
                    total_amount = contract_id.wage
                salary_rule_ids = contract_id.contract_salary_rule_ids
                if salary_rule_ids:
                    acc_salary_rule_id = salary_rule_ids.filtered(lambda l: l.salary_rule_id.code == "ACCOMMODATION")
                    if acc_salary_rule_id:
                        rule_total_amount = acc_salary_rule_id.amount
                        if end_of_month > contract_id.date_start > payslip.date_from:
                            salary_month_days = (end_of_month - contract_id.date_start).days + 1
                            rule_amount = (salary_month_days * rule_total_amount) / month_days
                            total_amount += rule_amount
                        elif payslip.date_from >= contract_id.date_start:
                            total_amount += rule_total_amount
                if gosi_salary_rule:
                    line_vals.append({
                        'sequence': gosi_salary_rule.sequence,
                        'code': gosi_salary_rule.code,
                        'name': gosi_salary_rule.name,
                        'salary_rule_id': gosi_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': (total_amount * -1 * .0975) or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': (total_amount * -1 * .0975) or 0,
                        'slip_id': payslip.id,
                    })

            else:
                start_of_month = date_utils.start_of(payslip.date_to, 'month')
                end_of_month = date_utils.end_of(payslip.date_to, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                total_amount = 0
                if end_of_month > contract_id.date_start > payslip.date_from:
                    wage = contract_id.wage
                    salary_month_days = (end_of_month - contract_id.date_start).days + 1
                    total_amount = (salary_month_days * wage) / month_days
                elif payslip.date_from >= contract_id.date_start:
                    total_amount = contract_id.wage
                salary_rule_ids = contract_id.contract_salary_rule_ids
                if salary_rule_ids:
                    acc_salary_rule_id = salary_rule_ids.filtered(lambda l: l.salary_rule_id.code == "ACCOMMODATION")
                    if acc_salary_rule_id:
                        rule_total_amount = acc_salary_rule_id.amount
                        if end_of_month > contract_id.date_start > payslip.date_from:
                            salary_month_days = (end_of_month - contract_id.date_start).days + 1
                            rule_amount = (salary_month_days * rule_total_amount) / month_days
                            total_amount += rule_amount
                        elif payslip.date_from >= contract_id.date_start:
                            total_amount += rule_total_amount
                if gosi_salary_rule:
                    gosi_line_amount = total_amount * 1 * .02
                    line_vals.append({
                        'sequence': gosi_allow_salary_rule.sequence,
                        'code': gosi_allow_salary_rule.code,
                        'name': gosi_allow_salary_rule.name,
                        'salary_rule_id': gosi_allow_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': (gosi_line_amount if gosi_line_amount <= 900 else 900) or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': (gosi_line_amount if gosi_line_amount <= 900 else 900) or 0,
                        'slip_id': payslip.id,
                    })

                    line_vals.append({
                        'sequence': gosi_salary_rule.sequence,
                        'code': gosi_salary_rule.code,
                        'name': gosi_salary_rule.name,
                        'salary_rule_id': gosi_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': (gosi_line_amount * -1 if gosi_line_amount <= 900 else -900) or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': (gosi_line_amount * -1 if gosi_line_amount <= 900 else -900) or 0,
                        'slip_id': payslip.id,
                    })

            # Check Other Payment Like: First Payslip Days
            if contract_id.other_first_payslip and contract_id.joining_date:
                start_of_month = date_utils.start_of(contract_id.joining_date, 'month')
                end_of_month = date_utils.end_of(contract_id.joining_date, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                extra_salary_days = (end_of_month - contract_id.joining_date).days + 1
                other_salary_rule = self.env.ref("pr_hr_payroll.hr_salary_rule_other_payments")
                gross_salary = contract_id.gross_amount
                extra_salary_amount = (extra_salary_days * gross_salary) / month_days
                if other_salary_rule and extra_salary_amount > 0:
                    line_vals.append({
                        'sequence': other_salary_rule.sequence,
                        'code': other_salary_rule.code,
                        'name': other_salary_rule.name,
                        'salary_rule_id': other_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': extra_salary_amount or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': extra_salary_amount or 0,
                        'slip_id': payslip.id,
                    })

                # Check GOSI Amount For These Days If Employee Is Saudi
                if payslip.employee_id.country_id and payslip.employee_id.country_id.is_homeland and contract_id.is_automatic_gosi:
                    gosi_salary_amount = contract_id.wage
                    salary_rule_ids = contract_id.contract_salary_rule_ids
                    if salary_rule_ids:
                        acc_salary_rule_id = salary_rule_ids.filtered(
                            lambda l: l.salary_rule_id.code == "ACCOMMODATION")
                        if acc_salary_rule_id:
                            gosi_salary_amount += acc_salary_rule_id.amount
                    extra_gosi_salary_amount = (extra_salary_days * gosi_salary_amount) / month_days
                    if gosi_salary_rule and extra_gosi_salary_amount > 0:
                        line_vals.append({
                            'sequence': gosi_salary_rule.sequence,
                            'code': gosi_salary_rule.code,
                            'name': gosi_salary_rule.name,
                            'salary_rule_id': gosi_salary_rule.id,
                            'contract_id': payslip.employee_id.contract_id.id,
                            'employee_id': payslip.employee_id.id,
                            'amount': (extra_gosi_salary_amount * -1 * .0975) or 0,
                            'quantity': 1,
                            'rate': 100,
                            'total': (extra_gosi_salary_amount * -1 * .0975) or 0,
                            'slip_id': payslip.id,
                        })

            # Contract Salary Rules
            if payslip.employee_id.contract_id and payslip.employee_id.contract_id.contract_salary_rule_ids:
                for salary_rule_line_id in payslip.employee_id.contract_id.contract_salary_rule_ids:
                    if salary_rule_line_id.pay_in_payslip:
                        salary_rule_id = salary_rule_line_id.sudo().salary_rule_id.sudo()
                        line_vals.append({
                            'sequence': salary_rule_id.sequence,
                            'code': salary_rule_id.code,
                            'name': salary_rule_id.name,
                            'salary_rule_id': salary_rule_id.id,
                            'contract_id': payslip.employee_id.contract_id.id,
                            'employee_id': payslip.employee_id.id,
                            'amount': salary_rule_line_id.sudo().amount or 0,
                            'quantity': 1,
                            'rate': 100,
                            'total': salary_rule_line_id.sudo().amount or 0,
                            'slip_id': payslip.id,
                        })

            # Calculate net and gross amounts, excluding "NET" and "GROSS" codes
            net_amount = sum(vals.get("total", 0) for vals in line_vals if vals.get("code") not in ["NET", "GROSS"])
            gross_amount = sum(
                vals.get("total", 0)
                for vals in line_vals
                # if vals.get("total", 0) > 0 and vals.get("code") not in ["NET", "GROSS", "BTA", "PAID86", "SICKTO88", "OTHER", "OVT"]
                if vals.get("total", 0) > 0 and vals.get("code") in ["BASIC", "ACCOMMODATION", "TRANSPORTATION", "FOT", "FOOD", "OTA"]
            )
            # Update the amounts in line_vals based on the code
            for val_line in line_vals:
                code = val_line.get("code")
                if code == "NET":
                    val_line["amount"] = net_amount
                    val_line["total"] = net_amount
                elif code == "GROSS":
                    val_line["amount"] = gross_amount
                    val_line["total"] = gross_amount
        return line_vals

    def check_payslip_dates(self):
        for payslip in self:
            payslip_days = (payslip.date_to - payslip.date_from).days + 1
            start_of_month = date_utils.start_of(payslip.date_to, 'month')
            end_of_month = date_utils.end_of(payslip.date_to, 'month')
            month_days = (end_of_month - start_of_month).days + 1
            for line in payslip.line_ids:
                if line.code not in ["GROSS", "NET"]:
                    amount = (line.total * payslip_days) / month_days
                    line.sudo().write({"amount": amount, "total": amount})
            # Calculate net and gross amounts, excluding "NET" and "GROSS" codes
            net_amount = sum(vals.total for vals in payslip.line_ids if vals.code not in ["NET", "GROSS"])
            gross_amount = sum(
                vals.total
                for vals in payslip.line_ids if vals.total > 0 and vals.code in ["BASIC", "ACCOMMODATION", "TRANSPORTATION", "FOT",
                                                                  "FOOD"]
            )
            # Update the amounts in line_vals based on the code
            for val_line in payslip.line_ids:
                code = val_line.code
                if code == "NET":
                    val_line.amount = net_amount
                    val_line.total = net_amount
                elif code == "GROSS":
                    val_line.amount = gross_amount
                    val_line.total = gross_amount

    def prepare_payslip_entry_vals_lines(self):
        for rec in self:
            payslip_entry_vals_lines = []
            if rec.state != 'done' :
                # raise UserError(_('Cannot mark payslip as paid if not confirmed.'))
                raise UserError(_('Cannot pay the payslip if not confirmed.'))
            if not rec.employee_id.employee_cost_center_id:
                raise ValidationError(
                    f"This employee {rec.employee_id.name} does not have cost center, please check !!")
            if not rec.employee_id.employee_account_id:
                raise ValidationError(
                    f"This employee {rec.employee_id.name} does not have account, please check !!")
            for line in rec.line_ids:
                if not line.salary_rule_id.account_id:
                    raise ValidationError(f"This salary rule {line.salary_rule_id.name} does not have account, please check !!")
                payslip_entry_line_vals = self.prepare_payslip_entry_line_vals(line=line)
                if payslip_entry_line_vals:
                    payslip_entry_vals_lines.append((0, 0, payslip_entry_line_vals))
            return payslip_entry_vals_lines

    def prepare_payslip_entry_line_vals(self, line):
        if (line.total != 0 or line.total > 0 or line.total < 0) and line.salary_rule_id.code not in ["GROSS", "NET"]:
            analytic_distribution = {
                str(self.employee_id.department_cost_center_id.id): 100,
                str(self.employee_id.section_cost_center_id.id): 100,
                str(self.employee_id.project_cost_center_id.id): 100,
                str(self.employee_id.employee_cost_center_id.id): 100,
                                     }
            # if line.slip_id.employee_id.department_id and line.slip_id.employee_id.department_id.department_cost_center_id:
            #     analytic_distribution.update({str(line.slip_id.employee_id.department_id.department_cost_center_id.id): 100})
            line_vals = {
                "account_id": line.salary_rule_id.account_id.id,
                "analytic_distribution": analytic_distribution,
            }
            # Project Manager
            if self.employee_id.project_cost_center_id and self.employee_id.project_cost_center_id.project_partner_id:
                line_vals.update({"partner_id": self.employee_id.project_cost_center_id.project_partner_id.id})
            if line.salary_rule_id.code in ["LOAN", "ADVALL"]:
                line_vals["account_id"] = line.slip_id.employee_id.employee_account_id.id

            if line.category_id.code in ["BASIC", "ALW"]:
                line_vals.update({
                    "name": f"{line.slip_id.employee_id.code} - {line.slip_id.employee_id.name} {line.salary_rule_id.name} of month {self.date_to.month} year {self.date_to.year}",
                    "debit": abs( line.total),
                    "credit": 0.0,
                })
            elif line.category_id.code == "DED":
                line_vals.update({
                    "name": f"{line.slip_id.employee_id.code} - {line.slip_id.employee_id.name} {line.salary_rule_id.name} of month {self.date_to.month} year {self.date_to.year}",
                    "credit": abs(line.total),
                    "debit": 0.0,
                })
            return line_vals
        else:
            return False

    def action_open_salary_journal_entry(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.salary_journal_entry_id.id,
            "views": [[self.env.ref('account.view_move_form').id, "form"]],
            "target": "current",
            "name": self.name
        }




