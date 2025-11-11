from odoo import http
from odoo.http import request

class AccountLedgerController(http.Controller):

    @http.route('/account_ledger/report/preview/<int:wizard_id>', type='http', auth='user')
    def account_ledger_preview(self, wizard_id):
        """Render the Account Ledger report as HTML for instant preview."""
        wizard = request.env['account.ledger'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()

        data = {
            'ids': [wizard.id],
            'model': wizard._name,
            'form': {
                'date_start': wizard.date_start.strftime('%Y-%m-%d'),
                'date_end': wizard.date_end.strftime('%Y-%m-%d'),
                'account': [wizard.account_id.id] if wizard.account_id else [],
                'company': wizard.company_id.id,
                'department': wizard.department_id.id if wizard.department_id else False,
                'section': wizard.section_id.id if wizard.section_id else False,
                'project': wizard.project_id.id if wizard.project_id else False,
                'employee': wizard.employee_id.id if wizard.employee_id else False,
                'asset': wizard.asset_id.id if wizard.asset_id else False,
            },
        }

        report_ref = 'account_ledger.acc_leg_report'

        html_content, _ = request.env['ir.actions.report']._render_qweb_html(
            report_ref, [wizard.id], data=data
        )

        headers = [('Content-Type', 'text/html; charset=utf-8')]
        return request.make_response(html_content, headers=headers)
