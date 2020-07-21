from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    voip_email = fields.Char(string="VOIP email", default="alianza@opmits.com", config_parameter='voip_email')
    ticket_grp = fields.Char(string="Target Ticket Group", default="Alianza Lost Calls", config_parameter='team_name')