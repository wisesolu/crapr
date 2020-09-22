from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    voip_email = fields.Char(string="VOIP emails", config_parameter='voip_email')