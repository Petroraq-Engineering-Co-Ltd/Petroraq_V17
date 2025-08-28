# -*- coding: utf-8 -*-
# from odoo import http


# class CustomPrSystem(http.Controller):
#     @http.route('/custom_pr_system/custom_pr_system', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_pr_system/custom_pr_system/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_pr_system.listing', {
#             'root': '/custom_pr_system/custom_pr_system',
#             'objects': http.request.env['custom_pr_system.custom_pr_system'].search([]),
#         })

#     @http.route('/custom_pr_system/custom_pr_system/objects/<model("custom_pr_system.custom_pr_system"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_pr_system.object', {
#             'object': obj
#         })

