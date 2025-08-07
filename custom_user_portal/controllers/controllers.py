from odoo import http
from odoo.http import request
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class PortalPR(http.Controller):

#showing page and getting manager name with id
    @http.route('/my/purchase-request/create', type='http', auth='user', website=True)
    def create_purchase_request(self, **kwargs):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        supervisor_name = ''
        supervisor_partner_id = ''
        if employee and employee.parent_id:
            supervisor = employee.parent_id
            if supervisor.user_id and supervisor.user_id.partner_id:
                supervisor_name = supervisor.user_id.partner_id.name
                supervisor_partner_id = supervisor.user_id.partner_id.id

        values = {
            'page_name': 'create_pr',
            'requested_by': employee.name if employee else user.name,
            'department': employee.department_id.name if employee and employee.department_id else '',
            'supervisor': supervisor_name,
            'supervisor_partner_id': supervisor_partner_id,
        }
        return request.render('custom_user_portal.portal_pr_form_template', values)

#getting all the products in inventory
    @http.route('/products', auth='public', type='json', website=True)
    def get_all_products(self, **kwargs):
        try:
            # Search for products with sudo() to ensure access
            products = request.env['product.template'].sudo().search([])
            product_list = [{
                'id': p.id,
                'name': p.name,
                'price': p.list_price,
                'type': p.type,
            } for p in products]
            
            # Add some default units if no products found
            if not product_list:
                product_list = [
                    {'id': 1, 'name': 'Pieces', 'price': 0.0, 'type': 'consu'},
                    {'id': 2, 'name': 'Units', 'price': 0.0, 'type': 'consu'},
                    {'id': 3, 'name': 'Boxes', 'price': 0.0, 'type': 'consu'},
                    {'id': 4, 'name': 'Kilos', 'price': 0.0, 'type': 'consu'},
                    {'id': 5, 'name': 'Liters', 'price': 0.0, 'type': 'consu'},
                ]
            
            return {'products': product_list}
        except Exception as e:
            return {'products': [], 'error': str(e)}

#getting the requested_by user and show all PR on portal
    @http.route('/my/purchase-request', type='http', auth='user', website=True)
    def portal_pr_list(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)

        pr_records = request.env['purchase.requisition'].sudo().search([
            ('requested_by', '=', employee.name)
        ])

        # Count by approval status
        pending_count = sum(1 for pr in pr_records if pr.approval == 'pending')
        approved_count = sum(1 for pr in pr_records if pr.approval == 'approved')
        rejected_count = sum(1 for pr in pr_records if pr.approval == 'rejected')

        return request.render('custom_user_portal.portal_purchase_request_list', {
            'prs': pr_records,
            'page_name': 'purchase_request',
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
        })
    
#Form submission
    @http.route('/my/purchase-request/submit', type='http', auth='user', methods=['POST'], csrf=True, website=True)
    def submit_purchase_request(self, **post):
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)

        requisition = request.env['purchase.requisition'].sudo().create({
            'requested_by': post.get('requested_by'),
            'department': post.get('department'),
            'supervisor': post.get('supervisor'),
            'supervisor_partner_id': int(post.get('supervisor_partner_id') or 0),
            'required_date': post.get('required_date'),
            'priority': post.get('priority'),
            'budget_type': post.get('budget_type_selector'),
            'budget_details': post.get('budget_input_field'),
            'notes': post.get('notes'),
        })

        line_items = []
        index = 1
        while f'item_description_{index}' in post:
            item = {
                'description': post.get(f'item_description_{index}'),
                'type': post.get(f'item_type_{index}'),
                'quantity': float(post.get(f'quantity_{index}') or 0),
                'unit': post.get(f'unit_{index}'),
                'unit_price': float(post.get(f'unit_price_{index}') or 0),
            }
            line_items.append(item)
            request.env['purchase.requisition.line'].sudo().create({
                'requisition_id': requisition.id,
                **item
            })
            index += 1

        manager = employee.parent_id if employee else False
        current_date = datetime.today().strftime('%Y-%m-%d')

        if manager and manager.work_email:
            line_rows = ""
            subtotal = 0
            for i, item in enumerate(line_items, 1):
                total_price = item['quantity'] * item['unit_price']
                subtotal += total_price
                line_rows += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{item['description']}</td>
                        <td>{item['type']}</td>
                        <td>{item['quantity']}</td>
                        <td>{item['unit']}</td>
                        <td>{item['unit_price']}</td>
                        <td>{total_price:.2f}</td>
                    </tr>
                """

            vat = subtotal * 0.15
            total = subtotal + vat

        if manager and manager.work_email:
            subject = f"New Purchase Requisition from {employee.name}"
            body_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                <p>Dear {manager.name},</p>

                <p><strong>{employee.name}</strong> has submitted a new <strong>Purchase Requisition</strong>.</p>
                <p><strong>Date of Request:</strong> {current_date}</p>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr><td><strong>Requested By:</strong></td><td>{post.get('requested_by')}</td></tr>
                    <tr><td><strong>Department:</strong></td><td>{post.get('department')}</td></tr>
                    <tr><td><strong>Supervisor:</strong></td><td>{post.get('supervisor')}</td></tr>
                    <tr><td><strong>Required Date:</strong></td><td>{post.get('required_date')}</td></tr>
                    <tr><td><strong>Priority:</strong></td><td>{post.get('priority')}</td></tr>
                    <tr><td><strong>Budget Type:</strong></td><td>{post.get('budget_type_selector')}</td></tr>
                    <tr><td><strong>Budget Details:</strong></td><td>{post.get('budget_input_field')}</td></tr>
                </table>

                <h4>Requested Items</h4>
                <table style="border-collapse: collapse; width: 100%; margin-bottom: 15px;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th style="border: 1px solid #ccc; padding: 8px;">#</th>
                            <th style="border: 1px solid #ccc; padding: 8px;">Item</th>
                            <th style="border: 1px solid #ccc; padding: 8px;">Type</th>
                            <th style="border: 1px solid #ccc; padding: 8px;">Qty</th>
                            <th style="border: 1px solid #ccc; padding: 8px;">Unit</th>
                            <th style="border: 1px solid #ccc; padding: 8px;">Unit Price</th>
                            <th style="border: 1px solid #ccc; padding: 8px;">Total</th>
                        </tr>
                    </thead>
                    <tbody>{line_rows}</tbody>
                    <tfoot>
                        <tr>
                            <td colspan="6" style="text-align:right; padding: 8px;"><strong>Subtotal</strong></td>
                            <td style="padding: 8px;">{subtotal:.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="6" style="text-align:right; padding: 8px;"><strong>VAT (15%)</strong></td>
                            <td style="padding: 8px;">{vat:.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="6" style="text-align:right; padding: 8px;"><strong>Total</strong></td>
                            <td style="padding: 8px;">{total:.2f}</td>
                        </tr>
                    </tfoot>
                </table>

                <p><strong>Additional Notes:</strong><br/>{post.get('notes') or 'N/A'}</p>

                <p style="margin-top: 20px;">Please log in to Odoo to view and approve the request.</p>
                <p>Best regards,<br/>Odoo Portal</p>
            </div>
            """

            # Send email
            request.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_to': manager.work_email,
                'email_from': request.env.user.email or 'noreply@yourcompany.com',
            }).send()

        return request.redirect('/my/purchase-request?pr_submitted=1')

