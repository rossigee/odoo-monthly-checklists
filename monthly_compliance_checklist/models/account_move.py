# -*- coding: utf-8 -*-

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        """Override create to trigger checklist updates"""
        move = super().create(vals)
        if move.state == 'posted':
            move._update_compliance_checklists()
        return move

    def write(self, vals):
        """Override write to trigger checklist updates when posted"""
        result = super().write(vals)
        if 'state' in vals and vals['state'] == 'posted':
            self._update_compliance_checklists()
        return result

    def _update_compliance_checklists(self):
        """Update related compliance checklist items when move is posted"""
        for move in self:
            if move.state != 'posted':
                continue

            # Get the month/year of the transaction
            move_date = move.date
            year = move_date.year
            month = move_date.month

            # Find active checklists for this month
            checklists = self.env['monthly.checklist'].search([
                ('year', '=', year),
                ('month', '=', month),
                ('state', '=', 'active')
            ])

            for checklist in checklists:
                # Force recomputation of check instances
                checklist.check_instances._compute_is_completed()

                # Recompute checklist totals
                checklist._compute_totals()
                checklist._compute_completion_percentage()
