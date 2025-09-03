from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PortalRFQ(http.Controller):

    @http.route("/my/rfq", type="http", auth="user", website=True)
    def my_rfq(self):
        partner = request.env.user.partner_id

        rfqs_vendor = (
            request.env["purchase.order"]
            .sudo()
            .search(
                [("partner_id", "=", partner.id), ("state", "in", ["draft", "sent"])]
            )
        )
        rfqs_following = (
            request.env["purchase.order"]
            .sudo()
            .search(
                [
                    ("message_follower_ids.partner_id", "=", partner.id),
                    ("state", "in", ["draft", "sent"]),
                ]
            )
        )

        rfqs = (rfqs_vendor | rfqs_following).filtered(
            lambda r: r.state in ["draft", "sent"]
        )

        return request.render("custom_user_portal.portal_rfq_template", {"rfqs": rfqs})

    @http.route(
        "/my/rfq/<int:rfq_id>/quotation", type="http", auth="user", website=True
    )
    def portal_create_rfq_quotation(self, rfq_id, **kw):
        rfq = request.env["purchase.order"].sudo().browse(rfq_id)
        rfq.custom_line_ids  # ensure it’s loaded
        company_registry = rfq.partner_id.company_registry
        return request.render(
            "custom_user_portal.portal_create_rfq_quotation_form",
            {"rfq": rfq, "company_registry": company_registry},
        )
    @http.route("/my/rfqs", type="http", auth="user", website=True)
    def my_rfq(self):
        partner = request.env.user.partner_id

        rfqs_following = (
            request.env["purchase.order"]
            .sudo()
            .search([
                ("message_follower_ids.partner_id", "=", partner.id),
                ("state", "in", ["draft", "sent"]),
            ])
        )

        return request.render(
            "custom_user_portal.portal_rfq_list_template",
            {"rfqs": rfqs_following},
        )
    @http.route("/my/rfqs/<int:rfq_id>", type="http", auth="user", website=True)
    def portal_rfq_view(self, rfq_id, **kw):
        partner = request.env.user.partner_id
        rfq = request.env["purchase.order"].sudo().browse(rfq_id)

        # Security check: only followers or vendor can see
        if partner not in rfq.message_follower_ids.mapped("partner_id") and partner.id != rfq.partner_id.id:
            return request.redirect("/my")  # not authorized

        rfq.custom_line_ids  # ensure lines are loaded

        # Fetch all quotations related to this RFQ
        quotations = request.env["purchase.quotation"].sudo().search([("rfq_origin", "=", rfq.name)])

        return request.render(
            "custom_user_portal.portal_rfq_view_template",
            {
                "rfq": rfq,
                "quotations": quotations,
            },
        )

    @http.route(
        "/my/rfq/<int:rfq_id>/quotation/submit",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def submit_rfq_quotation(self, rfq_id, **post):
        rfq = request.env["purchase.order"].sudo().browse(rfq_id)
        partner = request.env.user.partner_id

        # Create quotation record in your custom model
        quotation = (
            request.env["purchase.quotation"]
            .sudo()
            .create(
                {
                    "vendor_id": partner.id,
                    "pr_name": rfq.pr_name,
                    "rfq_origin": rfq.name,
                    "vendor_ref": rfq.partner_ref,
                    "notes": post.get("description"),
                    "order_deadline": post.get("quotation_valid_till"),
                    "expected_arrival": rfq.date_planned,
                    "supplier_name": post.get("supplier_name"),
                    "contact_person": post.get("contact_person"),
                    "company_address": post.get("company_address"),
                    "phone_number": post.get("phone_number"),
                    "email_address": post.get("email_address"),
                    "supplier_id": post.get("supplier_id"),
                    "quotation_ref": post.get("quotation_ref"),
                    # Payment Terms
                    "terms_net": bool(post.get("terms_net")),
                    "terms_30days": bool(post.get("terms_30days")),
                    "terms_advance": bool(post.get("terms_advance")),
                    "terms_advance_specify": (
                        post.get("terms_advance_specify")
                        if post.get("terms_advance")
                        else None
                    ),
                    "terms_delivery": bool(post.get("terms_delivery")),
                    "terms_other": bool(post.get("terms_other")),
                    "terms_others_specify": (
                        post.get("terms_others_specify")
                        if post.get("terms_others")
                        else None
                    ),
                    # Production / Material Availability
                    "ex_stock": bool(post.get("ex_stock")),
                    "required_days": bool(post.get("required_days")),
                    "production_days": (
                        post.get("production_days")
                        if post.get("required_days")
                        else None
                    ),
                    # Delivery Terms
                    "ex_work": bool(post.get("ex_work")),
                    "delivery_site": bool(post.get("delivery_site")),
                    # Delivery Date Expected
                    "delivery_date": post.get("delivery_date"),
                    # Delivery Method
                    "delivery_courier": bool(post.get("courier")),
                    "delivery_pickup": bool(post.get("pickup")),
                    "delivery_freight": bool(post.get("freight")),
                    "delivery_others": bool(post.get("delivery_others")),
                    "delivery_others_specify": (
                        post.get("delivery_others_specify")
                        if post.get("delivery_others")
                        else None
                    ),
                    # Partial Order Acceptable
                    "partial_yes": bool(post.get("partial_yes")),
                    "partial_no": bool(post.get("partial_no")),
                    "budget_type": rfq.budget_type,
                    "budget_code": rfq.budget_code,
                    "project_id": rfq.project_id.id,
                    #PO Info
                    "requested_by": rfq.requested_by,
                    "department": rfq.department,
                    "supervisor": rfq.supervisor,
                    "supervisor_partner_id": rfq.supervisor_partner_id,

                }
            )
        )
        product_indexes = set()
        for key in post:
            if key.startswith("product_description_"):
                try:
                    index = int(key.split("_")[-1])
                    product_indexes.add(index)
                except:
                    continue

        for i in sorted(product_indexes):
            description = post.get(f"product_description_{i}", "").strip()
            quantity = float(post.get(f"product_quantity_{i}", 0))
            unit = post.get(f"product_unit_{i}", "").strip()
            price_unit = float(post.get(f"product_price_{i}", 0))
            product_type = post.get(f"product_type_{i}", "").strip()

            if not description:
                continue

            request.env["purchase.quotation.line"].sudo().create(
                {
                    "quotation_id": quotation.id,
                    "name": description,
                    "quantity": quantity,
                    "type": product_type,
                    "unit": unit,
                    "price_unit": price_unit,
                }
            )

        all_quotations = (
            request.env["purchase.quotation"]
            .sudo()
            .search([("rfq_origin", "=", rfq.name)])
        )

        if all_quotations:
            min_total = min(all_quotations.mapped("total_incl_vat"))
            for q in all_quotations:
                q.is_best = q.total_incl_vat == min_total

        # ---------------- Email Notification Logic ----------------
        group_xml_ids = [
            "custom_user_portal.procurement_admin",
        ]

        recipient_users = request.env["res.users"].browse()
        for xml_id in group_xml_ids:
            try:
                # Use sudo() to avoid access error
                group = request.env.ref(xml_id).sudo()
                recipient_users |= group.users
            except ValueError:
                continue

        # Filter active users with email
        recipient_users = recipient_users.filtered(lambda u: u.active and u.email)

        # Email content
        subject = f"New Quotation Submitted for RFQ: {rfq.name}"
        body = f"""
        <p>Hello,</p>
        <p>A new quotation has been submitted by <strong>{partner.name}</strong> for RFQ <strong>{rfq.name}</strong>.</p>
        <p>
        Vendor Reference: {rfq.partner_ref or 'N/A'}<br/>
        Total Quotation Value (incl. VAT): {quotation.total_incl_vat:.2f}
        </p>
        <p>You can view it in the system for further action.</p>
        <p>Regards,<br/>Odoo Purchase System</p>
        """

        # Send email
        for user in recipient_users:
            request.env["mail.mail"].sudo().create(
                {
                    "subject": subject,
                    "body_html": body,
                    "email_to": user.email,
                }
            ).send()

        # ---------------- Create Activity for Procurement Users ----------------
        procurement_group = request.env.ref(
            "custom_user_portal.procurement_admin"
        ).sudo()
        for user in procurement_group.users:
            if user.active:
                request.env["mail.activity"].sudo().create(
                    {
                        "res_model_id": request.env["ir.model"]
                        ._get("purchase.quotation")
                        .id,
                        "res_id": quotation.id,
                        "activity_type_id": request.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "summary": "Review Quotation",
                        "user_id": user.id,
                        "note": f"Please review the Quotation for RFQ {rfq.name}.",
                        "date_deadline": quotation.order_deadline,
                    }
                )

        return request.redirect("/my/rfqs?quotation_submitted=1")
