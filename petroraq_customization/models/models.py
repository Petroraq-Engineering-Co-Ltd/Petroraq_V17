from odoo import models, fields, api
from markupsafe import Markup
from odoo.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = "Quotation"

    state = fields.Selection(
        selection_add=[
            ('to approve', 'Approval Pending'),
            ('reviewer_approved', 'Reviewer Approved'),
            ('approved', 'Approver Approved'),
            ('operations_approval', 'Operations Approval'),
            ('accounts_approval', 'Accounts Approval'),
            ('ceo_approval', 'CEO Approval')
        ]
    )
    overheads = fields.Float()
    risks = fields.Float()
    profit = fields.Float()
    total_global_overheads = fields.Float('Overheads Amount:', compute='_compute_total_global_factors')
    total_global_risks = fields.Float('Risks Amount', compute='_compute_total_global_factors')
    total_global_profit = fields.Float('Profit Amount:', compute='_compute_total_global_factors')
    partial_order_acceptable = fields.Selection([('yes', 'Yes'), ('no', 'No')], default='yes')

    def _compute_total_global_factors(self):
        for order in self:
            order.total_global_overheads = (order.overheads * order.amount_untaxed) / 100.0
            order.total_global_risks = (order.risks * order.amount_untaxed) / 100.0
            order.total_global_profit = (
                                                order.amount_untaxed + order.total_global_overheads + order.total_global_risks) * order.profit / 100.0

    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent', 'approved'}

    def action_confirm(self):
        if self.state == 'approved':

            # analytic_account_vals = self._prepare_analytic_account_data()
            #
            # section = None
            # for sale_line in self.order_line:
            #     if sale_line.display_type in ('line_section', 'line_note'):
            #         section = sale_line.name
            #     elif not sale_line.display_type:  # normal line
            #         sale_line.section_name = section  # custom field to store section
            #
            # result = self.order_line.read_group(domain=[('display_type', '=', False), ('section_name', '!=', False)], fields=['price_total:sum'],
            #                                     groupby=['section_name'])
            #
            # for array in result:
            #
            #     analytic_account_vals.update(
            #         {
            #             'name': array.get('section_name')
            #         }
            #     )
            #
            #     analytic = self.env['account.analytic.account'].create(analytic_account_vals)
            #
            #     self.env['crossovered.budget.lines'].create({
            #         'crossovered_budget_id': 1,
            #         'analytic_account_id': analytic.id,
            #         'date_from': '2026-01-01',
            #         'date_to': '2026-12-31',
            #         'planned_amount': array.get('price_total')
            #     })

            return super(SaleOrder, self).action_confirm()

        elif self.state == 'draft' and not self.user_has_groups('petroraq_customization.group_reviewer'):

            self.write(
                {
                    'state': 'to approve'
                }
            )

            users = self.env.ref('petroraq_customization.group_reviewer').users
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            message = _("<p>Sale order approval required <a href=%s >%s</a></p>") % (base_url, self.display_name)
            users.notify_info(message, title="Notification", sticky=True)

        # elif self.user_has_groups('petroraq_customization.group_approver'):
        #
        #     return super(SaleOrder, self).action_confirm()
        #
        # elif self.state == 'reviewer_approved' and not self.user_has_groups('petroraq_customization.group_approver'):
        #
        #     raise ValidationError(_('You don\'t have rights to confirm this quotation.'))

    def reviewer_approval_quotation(self):
        self.write({
            'state': 'reviewer_approved'
        })
        users = self.env.ref('petroraq_customization.group_approver').users
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        message = _("<p>Sale order approval required <a href=%s >%s</a></p>") % (base_url, self.display_name)
        users.notify_info(message, title="Notification", sticky=True)
        self.action_lock()

    def operations_approval_quotation(self):
        self.state = 'operations_approval'
        self.action_lock()

    def accounts_approval_quotation(self):
        self.state = 'accounts_approval'

    def ceo_approval_quotation(self):
        self.state = 'ceo_approval'

    def approver_quotation(self):
        self.write({
            'state': 'approved'
        })

    def create_workorder(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Workorder',
            'res_model': 'account.analytic.account',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {
                'default_partner_id': self.partner_id.id
            },
        }

    def button_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.rejection.reason',
            'view_mode': 'form',
            'views': [[self.env.ref('petroraq_customization.view_sale_order_cancel').id, 'form']],
            'target': 'new'
        }

    @api.depends('total_global_overheads', 'total_global_risks', 'total_global_profit')
    def _compute_amounts(self):
        super(SaleOrder, self)._compute_amounts()

        for order in self:
            order.amount_total = order.amount_untaxed + order.amount_tax + order.total_global_overheads + order.total_global_risks + order.total_global_profit


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    section_name = fields.Char()

    def _compute_tax_id(self):
        super(SaleOrderLine, self - self)._compute_tax_id()

    def _get_display_price(self):
        super(SaleOrderLine, self)._get_display_price()
        return self._origin.price_unit


class SaleRejectionReason(models.TransientModel):
    _name = "sale.rejection.reason"

    cancel_reason = fields.Text(
        string="Reason", required=True
    )

    def button_reject(self):
        sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
        msg = f'Quotation has been rejected.<br></br>Reason:- {self.cancel_reason}'
        sale_order.message_post(body=Markup(msg))
        sale_order.action_unlock()
        sale_order.state = 'draft'
