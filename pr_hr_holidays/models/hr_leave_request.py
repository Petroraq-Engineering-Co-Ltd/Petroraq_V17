from odoo import models, fields, api, _
from odoo.tools import date_utils
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import re
import json
import math
from random import randint
import logging
from datetime import datetime, timedelta
import pandas as pd


_logger = logging.getLogger(__name__)


class HrLeaveRequest(models.Model):
    """
    """
    # region [Initial]
    _name = 'pr.hr.leave.request'
    _description = 'Hr Leave Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string="Name")
    leave_type_id = fields.Many2one("hr.leave.type", string="Leave Type", required=True)
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    company_id = fields.Many2one('res.company', string='Company', tracking=True, required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, required=True)
    employee_manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True, readonly=True)
    hr_supervisor_ids = fields.Many2many('res.users', 'leave_request_hr_supervisor_users',  'hr_supervisor_id', 'leave_request_id', string='HR Supervisors', tracking=True, readonly=True)
    hr_manager_ids = fields.Many2many('res.users', 'leave_request_hr_manager_users',  'hr_manager_id', 'leave_request_id', string='HR Managers', tracking=True, readonly=True)
    reject_reason = fields.Text(string="Rejection Reason", readonly=True)
    note = fields.Text(string="Note")
    state = fields.Selection([
        ('draft', 'Submitted'),
        ('manager_approve', 'Manager Approved'),
        ('hr_supervisor', 'HR Supervisor Approved'),
        ('hr_approve', 'HR Manager Approved'),
        ('reject', 'Rejected'),
    ], default='draft', track_visibility='always',
        string='Status', required=True, index=True)
    approval_state = fields.Selection([
        ('draft', 'Pending Approval'),
        ('manager_approve', 'Pending Approval'),
        ('hr_supervisor', 'Pending Approval'),
        ('hr_approve', 'Approved'),
        ('reject', 'Rejected'),
    ], default='draft', track_visibility='always',
        string='Approval Status')
    employee_manager_check = fields.Boolean(compute="_compute_employee_manager_check")
    hr_supervisor_check = fields.Boolean(compute="_compute_hr_supervisor_check")
    hr_manager_check = fields.Boolean(compute="_compute_hr_manager_check")
    leave_id = fields.Many2one("hr.leave", string="Leave", readonly=True)

    # endregion [Fields]

    # region [Compute Methods]

    @api.depends("employee_id", "employee_id.parent_id", "employee_id.parent_id.user_id", "employee_manager_id", "employee_manager_id.user_id")
    def _compute_employee_manager_check(self):
        for rec in self:
            employee_manager_id = rec.employee_id.parent_id
            if employee_manager_id.user_id and employee_manager_id.user_id.id == self.env.user.id:
                rec.employee_manager_check = True
            else:
                rec.employee_manager_check = False

    def _compute_hr_supervisor_check(self):
        for rec in self:
            if self.env.user.has_group('pr_hr_holidays.custom_group_hr_holidays_supervisor'):
                rec.hr_supervisor_check = True
            else:
                rec.hr_supervisor_check = False

    def _compute_hr_manager_check(self):
        for rec in self:
            if self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
                rec.hr_manager_check = True
            else:
                rec.hr_manager_check = False

    # endregion [Compute Methods]


    # region [Onchange Methods]

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        self.ensure_one()
        if self.employee_id.company_id:
            self.company_id = self.employee_id.company_id.id

    # endregion [Onchange Methods]

    # region [Emails]

    def _prepare_email_vals(self, body_message, receiver):
        for rec in self:
            message = {
                "email_from": "hr@petroraq.com",
                "subject": f"{rec.employee_id.code} - Leave Request From {rec.date_from} To {rec.date_to}",
                "body_html": body_message,
                "email_to": receiver,
            }
            return message

    def _send_manager_email(self):
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = base_url + "/web#id=" + str(rec.id) + "&view_type=form&model=pr.hr.leave.request&view_type=form"

            body_message = f"""Dear Mr/Mrs. {rec.employee_id.parent_id.name},<br/><br/>

                We wish to inform you that your employee {rec.employee_id.name} has been asked for <strong>Leave Request From {rec.date_from} To {rec.date_to}</strong>.<br/><br/>
                You can check the request to take a decision by clicking this button <a class="btn btn-primary" href="{record_url}" role="button">Leave Request</a><br/><br/><br/>
                Thank you for your attention to this matter.<br/><br/>
                Best regards,<br/>
                <strong>HR Department</strong><br/>
                Petroraq Engineering
                """
            receiver = rec.employee_id.parent_id.work_email
            mail = self.env["mail.mail"]
            mail_id = mail.sudo().create(rec._prepare_email_vals(body_message=body_message, receiver=receiver))
            if mail_id:
                mail_id.sudo().send()

    def _send_hr_supervisor_email(self):
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = base_url + "/web#id=" + str(
                rec.id) + "&view_type=form&model=pr.hr.leave.request&view_type=form"

            # group_ids = [self.env.ref('hr_holidays.group_hr_holidays_user').id]
            group_ids = [self.env.ref('pr_hr_holidays.custom_group_hr_holidays_supervisor').id]
            user_ids = self.env['res.users'].sudo().search([('groups_id', 'in', group_ids)])
            if user_ids:
                for user in user_ids:
                    employee_id = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
                    if employee_id and employee_id.work_email:
                        body_message = f"""Dear Mr/Mrs. {employee_id.name},<br/><br/>

                            We wish to inform you that your employee {rec.employee_id.name} has been asked for <strong>Leave Request From {rec.date_from} To {rec.date_to}</strong>.<br/><br/>
                            You can check the request to take a decision by clicking this button <a class="btn btn-primary" href="{record_url}" role="button">Leave Request</a><br/><br/><br/>
                            Thank you for your attention to this matter.<br/><br/>
                            Best regards,<br/>
                            <strong>HR Department</strong><br/>
                            Petroraq Engineering
                            """
                        receiver = employee_id.work_email
                        mail = self.env["mail.mail"]
                        mail_id = mail.sudo().create(
                            rec._prepare_email_vals(body_message=body_message, receiver=receiver))
                        if mail_id:
                            mail_id.sudo().send()

    def _send_hr_manager_email(self):
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = base_url + "/web#id=" + str(rec.id) + "&view_type=form&model=pr.hr.leave.request&view_type=form"

            group_ids = [self.env.ref('hr_holidays.group_hr_holidays_manager').id]
            user_ids = self.env['res.users'].sudo().search([('groups_id', 'in', group_ids)])
            if user_ids:
                for user in user_ids:
                    employee_id = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
                    if employee_id and employee_id.work_email:
                        body_message = f"""Dear Mr/Mrs. {employee_id.name},<br/><br/>
            
                            We wish to inform you that your employee {rec.employee_id.name} has been asked for <strong>Leave Request From {rec.date_from} To {rec.date_to}</strong>.<br/><br/>
                            You can check the request to take a decision by clicking this button <a class="btn btn-primary" href="{record_url}" role="button">Leave Request</a><br/><br/><br/>
                            Thank you for your attention to this matter.<br/><br/>
                            Best regards,<br/>
                            <strong>HR Department</strong><br/>
                            Petroraq Engineering
                            """
                        receiver = employee_id.work_email
                        mail = self.env["mail.mail"]
                        mail_id = mail.sudo().create(
                            rec._prepare_email_vals(body_message=body_message, receiver=receiver))
                        if mail_id:
                            mail_id.sudo().send()

    def _send_result_to_employee(self, result):
        for rec in self:
            body_message = f"""Dear Mr/Mrs. {rec.employee_id.name},<br/><br/>

                We wish to inform you that your Leave Request {rec.name} has been <strong>{result}</strong>.<br/><br/>
                Thank you for your attention to this matter.<br/><br/>
                Best regards,<br/>
                <strong>HR Department</strong><br/>
                Petroraq Engineering
                """
            receiver = rec.employee_id.work_email
            mail = self.env["mail.mail"]
            mail_id = mail.sudo().create(rec._prepare_email_vals(body_message=body_message, receiver=receiver))
            if mail_id:
                mail_id.sudo().send()

    # endregion [Emails]

    # region [Actions]

    def action_manager_approve(self):
        for rec in self:
            rec = rec.sudo()
            rec.state = "manager_approve"
            rec.approval_state = "manager_approve"
            rec._send_hr_supervisor_email()

    def action_manager_reject(self):
        for rec in self:
            view = {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'pr.reject.record.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_record_id': '%s,%s' % (rec._name, rec.id),
                },
                'views': [(self.env.ref('pr_base.pr_reject_record_wizard_view_form').id, 'form')],
            }
            return view

    def action_hr_supervisor_approve(self):
        for rec in self:
            rec = rec.sudo()
            rec.state = "hr_supervisor"
            rec.approval_state = "hr_supervisor"
            rec._send_hr_manager_email()

    def action_hr_supervisor_reject(self):
        for rec in self:
            view = {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'pr.reject.record.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_record_id': '%s,%s' % (rec._name, rec.id),
                },
                'views': [(self.env.ref('pr_base.pr_reject_record_wizard_view_form').id, 'form')],
            }
            return view

    def action_hr_manager_approve(self):
        for rec in self:
            rec = rec.sudo()
            rec.state = "hr_approve"
            rec.approval_state = "hr_approve"
            leave_id = rec._create_employee_leave()
            rec._send_result_to_employee(result="Approved")

    def action_hr_manager_reject(self):
        for rec in self:
            view = {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'pr.reject.record.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_record_id': '%s,%s' % (rec._name, rec.id),
                },
                'views': [(self.env.ref('pr_base.pr_reject_record_wizard_view_form').id, 'form')],
            }
            return view

    def _create_employee_leave(self):
        for rec in self:
            leave_vals = {
                'name': f"{rec.employee_id.name} Leave From {rec.date_from} To {rec.date_to}",
                "employee_id": rec.employee_id.id,
                "holiday_status_id": rec.leave_type_id.id,
                "request_date_from": rec.date_from,
                "request_date_to": rec.date_to,
                "leave_request_id": rec.id,
            }
            leave_id = self.env["hr.leave"].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
            leave_skip_state_check=True
        ).sudo().create(leave_vals)
            if leave_id:
                rec.leave_id = leave_id.id
                # leave_id.sudo().action_approve()
                leave_id.sudo().state = "validate"
                return leave_id
            else:
                return False

    def action_open_leave(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.leave",
            "res_id": self.leave_id.id,
            "views": [[self.env.ref('hr_holidays.hr_leave_view_form').id, "form"]],
            "target": "current",
            "name": self.leave_id.name
        }

    # endregion [Actions]

    # region [Constrains]

    @api.constrains("state")
    def _check_reject_state(self):
        for rec in self:
            if rec.state == "reject":
                rec.approval_state = "reject"
                rec._send_result_to_employee(result="Rejected")

    # region [Constrains]

    # region [Crud]

    @api.model
    def create(self, vals):
        '''
        We Inherit Create Method To Pass Sequence Fo Field Name
        '''
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('hr.holidays.leave.request.seq.code') or ''
        employee_manager_id = res.employee_id.parent_id
        if employee_manager_id:
            res.employee_manager_id = employee_manager_id.id
        hr_supervisor_group_ids = [self.env.ref('pr_hr_holidays.custom_group_hr_holidays_supervisor').id]
        hr_manager_group_ids = [self.env.ref('hr_holidays.group_hr_holidays_manager').id]
        hr_supervisor_ids = self.env['res.users'].sudo().search([('groups_id', 'in', hr_supervisor_group_ids)])
        hr_manager_ids = self.env['res.users'].sudo().search([('groups_id', 'in', hr_manager_group_ids)])
        if hr_supervisor_ids:
            res.hr_supervisor_ids = hr_supervisor_ids.ids
        if hr_manager_ids:
            res.hr_manager_ids = hr_manager_ids.ids
        res.sudo()._send_manager_email()
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("This Leave Request Should Be Draft To Can Delete !!")
        return super().unlink()

    # endregion [Crud]



