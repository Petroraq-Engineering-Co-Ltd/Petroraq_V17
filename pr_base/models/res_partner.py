# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_code = fields.Char(string='Code', required=True)
    arabic_name = fields.Char(string='Arabic Name', required=True)
    arabic_street = fields.Char(string='Arabic Street', required=True)
    arabic_street2 = fields.Char(string='Arabic Street', required=True)







