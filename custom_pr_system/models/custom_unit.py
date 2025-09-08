from odoo import models, fields

class CustomUnit(models.Model):
    _name = 'custom.unit'
    _description = 'Custom Units'

    name = fields.Char(string="Unit Name", required=True)
    _sql_constraints = [
        ('unique_unit_name', 'unique(name)', 'The Unit Name must be unique!')
    ]


class AddUnitWizard(models.TransientModel):
    _name = "add.unit.wizard"
    _description = "Add Unit Wizard"

    name = fields.Char(string="Unit Name", required=True)

    def action_add_unit(self):
        # create new unit
        new_unit = self.env['custom.unit'].create({'name': self.name})

        # return back to PR line form with the new unit preselected
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pr.line',
            'view_mode': 'form',
            'res_id': self.env.context.get('active_id'),
            'target': 'current',
            'context': dict(self.env.context, default_unit=new_unit.id),
        }

