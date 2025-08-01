# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPrintJournal(models.TransientModel):
    _inherit = "account.common.journal.report"
    _name = "account.print.journal"
    _description = "Account Print Journal"

    sort_selection = fields.Selection([('date', 'Date'), ('move_name', 'Journal Entry Number'),], 'Entries Sorted by', required=True, default='move_name')
    # journal_ids = fields.Many2many('account.journal', string='Journals', required=False, default=lambda self: self.env['account.journal'].search([('type', 'in', ['sale', 'purchase'])]))
    journal_ids = fields.Many2many('account.journal', string='Journals', required=False, domain="[('company_id', '=', company_id), ('type', 'in', ['sale', 'purchase'])]")

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return self.env.ref('account.action_report_journal').with_context(landscape=True).report_action(self, data=data)
