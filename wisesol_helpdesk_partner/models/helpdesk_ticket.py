# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def find_partner(self):
        for msg in self.message_ids:
            if msg.author_id.name == self.env['ir.config_parameter'].sudo().get_param('voip_email'):
                r = re.compile(r'\D\d{10}\D')
                results = r.findall(msg.body)
                if results:
                    partners = self.env['res.partner'].search([('phone', 'like', '{}%{}%{}'.format(results[0][1:4],results[0][4:7],results[0][7:11]))])
                    if partners:
                        oldest = partners.sorted(key='x_studio_age', reverse=True)[0]
                        self.partner_id = oldest