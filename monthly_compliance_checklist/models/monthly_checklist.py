# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MonthlyChecklist(models.Model):
    _name = "monthly.checklist"
    _description = "Monthly Compliance Checklist"
    _inherit = ["mail.thread"]
    _order = "period_date desc"
    _rec_name = "period_display"
    _sql_constraints = [
        (
            "unique_period",
            "UNIQUE(period_date)",
            "A checklist already exists for this period!",
        )
    ]
    period_date = fields.Date(
        string="Period",
        required=True,
        tracking=True,
        help="Month/year for this checklist (day is always set to 1st)",
    )

    # Computed year/month for compatibility and display
    year = fields.Integer(string="Year", compute="_compute_year_month", store=True)
    month = fields.Integer(string="Month", compute="_compute_year_month", store=True)
    period_display = fields.Char(
        string="Period", compute="_compute_period_display", store=True
    )

    # Status tracking
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    notes = fields.Text(
        string="Notes", help="Additional notes about this monthly checklist"
    )

    completion_percentage = fields.Float(
        string="Completion %", compute="_compute_completion_percentage", store=True
    )

    # Relationships - simplified design
    check_instances = fields.One2many(
        "check.instance",
        "checklist_id",
        string="Check Instances",
        help="Monthly instances of applicable check templates",
    )

    # Computed fields
    total_items = fields.Integer(
        string="Total Items", compute="_compute_totals", store=True
    )
    completed_items = fields.Integer(
        string="Completed Items", compute="_compute_totals", store=True
    )

    @api.depends("period_date")
    def _compute_year_month(self):
        for record in self:
            if record.period_date:
                record.year = record.period_date.year
                record.month = record.period_date.month
            else:
                record.year = 0
                record.month = 0

    @api.depends("period_date")
    def _compute_period_display(self):
        for record in self:
            if record.period_date:
                record.period_display = record.period_date.strftime("%Y-%m")
            else:
                record.period_display = ""

    @api.onchange("period_date")
    def _onchange_period_date(self):
        """Normalize period_date to always be the 1st of the month"""
        if self.period_date:
            from datetime import date

            self.period_date = date(self.period_date.year, self.period_date.month, 1)

    @api.depends("check_instances", "check_instances.is_completed")
    def _compute_totals(self):
        for record in self:
            record.total_items = len(record.check_instances)
            record.completed_items = len(
                record.check_instances.filtered("is_completed")
            )

    @api.depends("total_items", "completed_items")
    def _compute_completion_percentage(self):
        for record in self:
            if record.total_items > 0:
                record.completion_percentage = (
                    record.completed_items / record.total_items
                ) * 100
            else:
                record.completion_percentage = 0.0

    @api.model
    def create(self, vals):
        """Override create to generate check instances"""
        checklist = super().create(vals)
        checklist._generate_check_instances()
        checklist.state = "active"
        return checklist

    def _generate_check_instances(self):
        """Generate check instances from applicable check templates"""
        # Get all check templates
        check_templates = self.env["check.template"].search([])

        # Create instances for templates applicable to this month
        for template in check_templates:
            if template.is_applicable_for_month(self.year, self.month):
                template.create_check_instance(self.id)

    def action_complete(self):
        """Mark checklist as completed"""
        self.state = "completed"

    def action_reopen(self):
        """Reopen completed checklist"""
        self.state = "active"

    @api.model
    def create_current_month_checklist(self):
        """Create monthly checklist for current month (called by cron)"""
        from datetime import date

        today = date.today()
        period_date = date(today.year, today.month, 1)  # Always 1st of month

        # Check if checklist already exists for this month
        existing = self.search([("period_date", "=", period_date)])

        if not existing:
            self.create(
                {
                    "period_date": period_date,
                }
            )
