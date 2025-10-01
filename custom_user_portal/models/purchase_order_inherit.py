from odoo import models

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_send_purchase_order_email(self):
        """Send email to vendor with Purchase Order details and custom quotation lines.

        This builds the email entirely in Python (no external mail templates),
        using the fields discussed: vendor, vendor_ref, RFQ origin, planned date,
        project + budget fields, PR info, and both quotation custom lines and PO lines.
        """
        self.ensure_one()

        # Recipient
        email_to = self.partner_id and self.partner_id.email or False
        if not email_to:
            # No recipient; do nothing gracefully
            return True

        # Header fields (read defensively for custom attrs)
        vendor_name = self.partner_id.display_name or ''
        vendor_ref = self.partner_ref or ''
        rfq_origin = self.name or ''
        planned = self.date_planned or ''

        project_name = getattr(self, 'project_id', False) and self.project_id.display_name or ''
        budget_type = getattr(self, 'budget_type', '') or ''
        budget_code = getattr(self, 'budget_code', '') or ''
        pr_name = getattr(self, 'pr_name', '') or ''
        requested_by = getattr(self, 'requested_by', '') or ''
        department = getattr(self, 'department', '') or ''
        supervisor = getattr(self, 'supervisor', '') or ''

        total_amount = getattr(self, 'amount_total', 0.0)

        # Build HTML sections
        summary_html = f"""
        <h3 style="margin-top:16px;">Summary</h3>
        <table border="0" cellspacing="0" cellpadding="4" style="width:100%;">
          <tr>
            <td style="width:25%;"><strong>Vendor</strong></td>
            <td>{vendor_name}</td>
            <td style="width:25%;"><strong>Vendor Ref</strong></td>
            <td>{vendor_ref}</td>
          </tr>
          <tr>
            <td><strong>RFQ Origin</strong></td>
            <td>{rfq_origin}</td>
            <td><strong>Expected Arrival</strong></td>
            <td>{planned}</td>
          </tr>
          <tr>
            <td><strong>Project</strong></td>
            <td>{project_name}</td>
            <td><strong>PR Name</strong></td>
            <td>{pr_name}</td>
          </tr>
          <tr>
            <td><strong>Requested By</strong></td>
            <td>{requested_by}</td>
            <td><strong>Department</strong></td>
            <td>{department}</td>
          </tr>
          <tr>
            <td><strong>Supervisor</strong></td>
            <td>{supervisor}</td>
             <td><strong>Quotation Ref No</strong></td>
            <td>{rfq_origin}</td>
          </tr>
        </table>
        """

        # Custom quotation lines (if your PO has custom_line_ids)
        custom_lines = getattr(self, 'custom_line_ids', False)
        custom_lines_html = ''
        if custom_lines:
            rows = []
            for ln in custom_lines:
                rows.append(
                    f"<tr>"
                    f"<td>{ln.name or ''}</td>"
                    f"<td>{ln.quantity or 0}</td>"
                    f"<td>{ln.type or ''}</td>"
                    f"<td>{ln.unit or ''}</td>"
                    f"<td>{ln.price_unit or 0}</td>"
                    f"</tr>"
                )
            custom_lines_html = (
                "<h3 style=\"margin-top:24px;\">Quotation Lines</h3>"
                "<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\" style=\"border-collapse: collapse; width: 100%;\">"
                "<thead><tr style=\"background-color:#f2f2f2;\">"
                "<th>Description</th><th>Quantity</th><th>Type</th><th>Unit</th><th>Unit Price</th>"
                "</tr></thead><tbody>" + ''.join(rows) + "</tbody></table>"
            )

        # Standard PO lines (commented out per request)
        # po_rows = []
        # for line in self.order_line:
        #     po_rows.append(
        #         f"<tr>"
        #         f"<td>{line.product_id.display_name or ''}</td>"
        #         f"<td>{line.name or ''}</td>"
        #         f"<td>{line.product_qty or 0}</td>"
        #         f"<td>{line.price_unit or 0}</td>"
        #         f"<td>{line.price_subtotal or 0}</td>"
        #         f"</tr>"
        #     )
        # po_lines_html = (
        #     "<h3 style=\"margin-top:24px;\">Purchase Order Lines</h3>"
        #     "<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\" style=\"border-collapse: collapse; width: 100%;\">"
        #     "<thead><tr style=\"background-color:#f2f2f2;\">"
        #     "<th>Product</th><th>Description</th><th>Quantity</th><th>Unit Price</th><th>Subtotal</th>"
        #     "</tr></thead><tbody>" + ''.join(po_rows) + "</tbody></table>"
        # )
        po_lines_html = ""

        body = f"""
        <p>Dear {vendor_name},</p>
        <p>Please find below the details of Purchase Order <strong>{self.name}</strong>:</p>
        {summary_html}
        {custom_lines_html}
        {po_lines_html}
        <p style="margin-top:16px;">Regards,<br/>{self.env.user.name}</p>
        """

        subject = f"Purchase Order: {self.name}"
        email_from = self.env.user.email_formatted or (self.company_id and self.company_id.email) or False

        mail_vals = {
            'subject': subject,
            'body_html': body,
            'email_to': email_to,
        }
        if email_from:
            mail_vals['email_from'] = email_from

        self.env['mail.mail'].sudo().create(mail_vals).send()

        # Log in chatter
        try:
            to_display = self.partner_id.display_name if self.partner_id else email_to
            self.message_post(
                body=f"Email sent to {to_display} ({email_to})",
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        except Exception:
            # Do not block on chatter logging errors
            pass

        # Mark RFQ as sent, like the native "Send by Email"
        if self.state == 'draft':
            try:
                # Use standard PO state so PR sync mapping (sent -> rfq_sent) works
                self.write({'state': 'sent'})
            except Exception:
                pass
        return True
