from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    voip_email = fields.Char(string="VOIP email", default="alianza@opmits.com", config_parameter='voip_email')