from odoo import models, fields, api

class Message(models.Model):

    _inherit = 'mail.message'
    
    def create(self, values_list):
        res = super(Message, self).create(values_list)
        if res.model == 'helpdesk.ticket':
            ticket = self.env['helpdesk.ticket'].browse([res.res_id])
            ticket.find_partner()
        return res