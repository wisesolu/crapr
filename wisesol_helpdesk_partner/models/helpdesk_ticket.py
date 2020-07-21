# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def find_partner(self):
        for msg in self.message_ids:
            if msg.author_id.name == self.env['ir.config_parameter'].sudo().get_param('voip_email'):
                r = re.compile(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})')
                results = r.findall(msg.body)
                if results:
                    partners = self.env['res.partner'].search([('phone', 'like', '{}%{}%{}'.format(results[0][0:2],results[0][3:5],results[0][6:9]))])
                    if partners:
                        oldest = partners.sorted(key='age', reverse=True)[0]
                        self.partner_id = oldest