# -*- coding: utf-8 -*-
# from odoo import http


# class PetroraqCustomization(http.Controller):
#     @http.route('/petroraq_customization/petroraq_customization', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/petroraq_customization/petroraq_customization/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('petroraq_customization.listing', {
#             'root': '/petroraq_customization/petroraq_customization',
#             'objects': http.request.env['petroraq_customization.petroraq_customization'].search([]),
#         })

#     @http.route('/petroraq_customization/petroraq_customization/objects/<model("petroraq_customization.petroraq_customization"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('petroraq_customization.object', {
#             'object': obj
#         })

