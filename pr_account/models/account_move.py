from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import json


class AccountMove(models.Model):
    # region [Initial]
    _inherit = 'account.move'
    # endregion [Initial]

    old_id = fields.Integer(string="Old ID")
    journal_voucher_view = fields.Boolean()

    def _search_default_journal(self):
        if self.payment_id and self.payment_id.journal_id:
            return self.payment_id.journal_id
        if self.statement_line_id and self.statement_line_id.journal_id:
            return self.statement_line_id.journal_id
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        journal_types = self._get_valid_journal_types()
        company = self.company_id or self.env.company
        domain = [
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', journal_types),
        ]

        journal = None
        # the currency is not a hard dependence, it triggers via manual add_to_compute
        # avoid computing the currency before all it's dependences are set (like the journal...)
        if self.env.cache.contains(self, self._fields['currency_id']):
            currency_id = self.currency_id.id or self._context.get('default_currency_id')
            if currency_id and currency_id != company.currency_id.id:
                currency_domain = domain + [('currency_id', '=', currency_id)]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, order="id asc", limit=1)

        if not journal:
            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal

    def get_attachments_data(self):
        for move in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            response = requests.request('GET',
                                        url=f"https://shakilkhan8-petroraq-engineering-services.odoo.com/api/journal_entry/attachments",
                                        timeout=60)
            if response.status_code == 200:
                response_json = response.json()
                result = response_json.get("result")
                for k, v in result.items():
                    journal_entry_id = self.env["account.move"].search([("old_id", "=", int(k))], limit=1)
                    if journal_entry_id:
                        attachment_ids = []
                        for attachment_item in v:
                            attachment = {
                                'res_name': attachment_item.get("res_name"),
                                'res_model': 'account.move',
                                'res_id': journal_entry_id.id,
                                'datas': attachment_item.get("datas"),
                                'type': 'binary',
                                'name': attachment_item.get("name"),
                            }
                            attachment_obj = self.env['ir.attachment']
                            att_record = attachment_obj.sudo().create(attachment)
                            attachment_ids.append(att_record.id)
                        if attachment_ids:
                            journal_entry_id.sudo().update({'attachment_ids': [(6, 0, attachment_ids)]})
                            print("success")
