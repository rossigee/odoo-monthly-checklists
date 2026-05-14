# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models


class ComplianceBackfillWizard(models.TransientModel):
    _name = 'compliance.backfill.wizard'
    _description = 'Backfill Compliance Checklists Wizard'

    template_id = fields.Many2one(
        'compliance.template',
        string='Template',
        required=True
    )
    start_year = fields.Integer(
        string='Start Year',
        required=True,
        default=lambda self: date.today().year
    )
    start_month = fields.Integer(
        string='Start Month',
        required=True,
        default=1
    )
    end_year = fields.Integer(
        string='End Year',
        required=True,
        default=lambda self: date.today().year
    )
    end_month = fields.Integer(
        string='End Month',
        required=True,
        default=lambda self: date.today().month - 1
    )
    skip_existing = fields.Boolean(
        string='Skip Existing Checklists',
        default=True,
        help='Skip months that already have checklists'
    )

    # Summary fields
    months_to_create = fields.Text(
        string='Months to Create',
        compute='_compute_months_to_create',
        help='List of months that will be created'
    )

    @api.depends('start_year', 'start_month', 'end_year', 'end_month', 'template_id', 'skip_existing')
    def _compute_months_to_create(self):
        for wizard in self:
            if not all([wizard.start_year, wizard.start_month, wizard.end_year, wizard.end_month]):
                wizard.months_to_create = ""
                continue

            months = wizard._get_months_to_create()
            if months:
                month_strings = [f"{year}/{month:02d}" for year, month in months]
                wizard.months_to_create = ", ".join(month_strings)
            else:
                wizard.months_to_create = "No months to create"

    def _get_months_to_create(self):
        """Get list of (year, month) tuples to create"""
        months = []

        # Validate date range
        start_date = date(self.start_year, self.start_month, 1)
        end_date = date(self.end_year, self.end_month, 1)

        if start_date > end_date:
            return months

        # Generate month list
        current_year = self.start_year
        current_month = self.start_month

        while True:
            # Check if we should skip existing
            if self.skip_existing and self.template_id:
                existing = self.env['monthly.checklist'].search([
                    ('template_id', '=', self.template_id.id),
                    ('year', '=', current_year),
                    ('month', '=', current_month)
                ])
                if not existing:
                    months.append((current_year, current_month))
            else:
                months.append((current_year, current_month))

            # Break if we've reached the end
            if current_year == self.end_year and current_month == self.end_month:
                break

            # Move to next month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return months

    @api.constrains('start_year', 'start_month', 'end_year', 'end_month')
    def _check_date_range(self):
        for wizard in self:
            if wizard.start_year and wizard.end_year:
                start_date = date(wizard.start_year, wizard.start_month or 1, 1)
                end_date = date(wizard.end_year, wizard.end_month or 12, 1)

                if start_date > end_date:
                    raise models.ValidationError("Start date must be before or equal to end date")

                # Don't allow future dates
                today = date.today()
                if end_date > today.replace(day=1):
                    raise models.ValidationError("Cannot create checklists for future months")

    def action_create_checklists(self):
        """Create the checklists for specified date range"""
        if not self.template_id:
            raise models.UserError("Template is required")

        months_to_create = self._get_months_to_create()

        if not months_to_create:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Checklists Created',
                    'message': 'No months found that need checklist creation.',
                    'type': 'info'
                }
            }

        checklist_model = self.env['monthly.checklist']
        created_checklists = []

        for year, month in months_to_create:
            # Double-check for existing if skip_existing is enabled
            if self.skip_existing:
                existing = checklist_model.search([
                    ('template_id', '=', self.template_id.id),
                    ('year', '=', year),
                    ('month', '=', month)
                ])
                if existing:
                    continue

            # Create the checklist
            checklist = checklist_model.create({
                'template_id': self.template_id.id,
                'year': year,
                'month': month,
                'name': f"{self.template_id.name} - {year}/{month:02d}"
            })
            created_checklists.append(checklist)

        # Show success message
        count = len(created_checklists)
        message = f"Successfully created {count} checklist{'s' if count != 1 else ''}"

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Checklists Created',
                'message': message,
                'type': 'success'
            }
        }

        # If checklists were created, show them
        if created_checklists:
            return {
                'name': 'Created Checklists',
                'type': 'ir.actions.act_window',
                'res_model': 'monthly.checklist',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', [c.id for c in created_checklists])],
                'context': {'search_default_group_by_year_month': 1}
            }

        return notification
