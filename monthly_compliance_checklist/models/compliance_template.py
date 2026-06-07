# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ComplianceTemplate(models.Model):
    _name = "compliance.template"
    _description = "Compliance Template"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Template Name", required=True, tracking=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True, tracking=True)
    auto_create_monthly = fields.Boolean(
        string="Auto Create Monthly",
        default=True,
        help="Automatically create monthly checklists based on this template",
    )

    # Template configuration removed - using template items instead

    # Relationships
    monthly_checklists = fields.One2many(
        "monthly.checklist", "template_id", string="Monthly Checklists"
    )

    @api.model
    def create_monthly_checklists(self):
        """Cron job method to create monthly checklists"""
        current_date = fields.Date.today()
        year = current_date.year
        month = current_date.month

        # Get all active templates
        templates = self.search(
            [("active", "=", True), ("auto_create_monthly", "=", True)]
        )

        checklist_model = self.env["monthly.checklist"]

        for template in templates:
            # Check if checklist already exists for this month
            existing = checklist_model.search(
                [
                    ("template_id", "=", template.id),
                    ("year", "=", year),
                    ("month", "=", month),
                ]
            )

            if not existing:
                checklist_model.create(
                    {
                        "template_id": template.id,
                        "year": year,
                        "month": month,
                        "name": f"{template.name} - {year}/{month:02d}",
                    }
                )

        return True

    def action_backfill_checklists(self):
        """Wizard to backfill checklists for past months"""
        return {
            "name": "Backfill Monthly Checklists",
            "type": "ir.actions.act_window",
            "res_model": "compliance.backfill.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_template_id": self.id},
        }
