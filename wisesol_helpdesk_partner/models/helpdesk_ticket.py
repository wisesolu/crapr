# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import re, logging

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    phone_lost = fields.Char(string=_('Lost Phone Number'))

    @api.model
    def extract_msg_details(self, msg):
        '''Extracts the phone number from the body of a msg and finds the contact with that number.'''
        emails = self.env['ir.config_parameter'].sudo().get_param('voip_email').split(',')
        if self.env['res.partner'].browse([msg['author_id']]).email_normalized in emails:
            r = re.compile(r'\d{10}')
            results = r.findall(msg['body'])
            if results:
                partners = self.env['res.partner'].search([('phone', 'like', '{}%{}%{}'.format(results[0][0:3], results[0][3:6], results[0][6:10]))])
                if partners:
                    oldest = partners.sorted(key='create_date')[0]
                    return {'phone_lost': results[0], 'partner_id': oldest.id, 'partner_email': oldest.email}
                else:
                    return {'phone_lost': results[0]}

    @api.model
    def message_new(self, msg, custom_values=None):
        ticket = super(HelpdeskTicket, self).message_new(msg, custom_values)
        partner_values = self.extract_msg_details(msg)
        if partner_values:
            ticket.write(partner_values)
        return ticket
