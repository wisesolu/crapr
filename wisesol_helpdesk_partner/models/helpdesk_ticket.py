# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re, logging

_logger = logging.getLogger(__name__)

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def find_partner(self):
        if self.message_ids.sorted(key='create_date', reverse=True) and self.env['ir.config_parameter'].sudo().get_param('voip_email').split(","):
            msg = self.message_ids.sorted(key='create_date', reverse=True)[0]
            emails = self.env['ir.config_parameter'].sudo().get_param('voip_email').split(",")
            for email in emails:
                if msg.author_id.email_normalized == email:
                    r = re.compile(r'\D\d{10}\D')
                    results = r.findall(msg.body)
                    if results:
                        partners = self.env['res.partner'].search([('phone', 'like', '{}%{}%{}'.format(results[0][1:4],results[0][4:7],results[0][7:11]))])
                        default_partner = self.env['res.partner'].search([('name', '=', 'alianza@opmits.com')])
                        if partners:
                            oldest = partners.sorted(key='x_studio_age', reverse=True)[0]
                            self.partner_id = oldest
                            self.partner_email = oldest.email
                        else:
                            self.partner_id = default_partner.id