# -*- coding: utf-8 -*-

import calendar

from odoo import api, fields, models


class WaterBillCompliance(models.Model):
    """
    Water Bill Compliance Condition

    Validates the complete water bill payment process:
    1. Water usage data imported (non-zero consumption)
    2. Invoice created with attachment (above minimum amount)
    3. Payment processed with attachment
    4. Bank statement reconciles the payment
    5. Invoice marked as reconciled
    6. Summary posted to communication channel
    """

    _name = "water.bill.compliance"
    _inherit = "compliance.condition.abstract"
    _description = "Water Bill Compliance Condition"

    partner_id = fields.Many2one(
        "res.partner",
        string="Utility Provider",
        help="Water utility company partner to filter invoices by",
    )
    minimum_amount = fields.Float(
        string="Minimum Expected Amount",
        default=25.0,
        help="Minimum expected invoice amount for validation",
    )
    maximum_consumption_variance = fields.Float(
        string="Max Consumption Variance %",
        default=50.0,
        help="Maximum allowed variance from previous month consumption",
    )

    consumption_units = fields.Float(
        string="Consumption (Units)", help="Water consumption units for this month"
    )
    previous_month_consumption = fields.Float(
        string="Previous Month Consumption",
        compute="_compute_previous_consumption",
        help="Previous month consumption for variance analysis",
    )
    consumption_variance_percent = fields.Float(
        string="Consumption Variance %",
        compute="_compute_consumption_variance",
        help="Percentage change from previous month",
    )

    step_1_data_imported = fields.Boolean(
        string="Usage Data Imported",
        default=False,
        help="Water usage data has been imported",
    )
    step_2_invoice_created = fields.Boolean(
        string="Invoice Created",
        default=False,
        help="Invoice has been created with proper attachment",
    )
    step_3_payment_processed = fields.Boolean(
        string="Payment Processed",
        default=False,
        help="Payment has been processed with attachment",
    )
    step_4_bank_reconciled = fields.Boolean(
        string="Bank Reconciled",
        default=False,
        help="Bank statement has been reconciled",
    )
    step_5_invoice_reconciled = fields.Boolean(
        string="Invoice Reconciled",
        default=False,
        help="Invoice has been marked as reconciled",
    )
    step_6_notification_sent = fields.Boolean(
        string="Notification Sent",
        default=False,
        help="Summary has been posted to communication channel",
    )

    @api.depends("year", "month")
    def _compute_previous_consumption(self):
        """Get previous month's consumption for variance analysis"""
        for condition in self:
            if not condition.year or not condition.month:
                condition.previous_month_consumption = 0.0
                continue

            prev_month = condition.month - 1
            prev_year = condition.year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1

            if "water.usage" not in self.env:
                condition.previous_month_consumption = 0.0
                continue

            prev_usage = self.env["water.usage"].search(
                [("year", "=", prev_year), ("month", "=", prev_month)], limit=1
            )

            condition.previous_month_consumption = (
                prev_usage.consumption_units if prev_usage else 0.0
            )

    @api.depends("consumption_units", "previous_month_consumption")
    def _compute_consumption_variance(self):
        """Calculate consumption variance percentage"""
        for condition in self:
            if condition.previous_month_consumption > 0:
                variance = (
                    (condition.consumption_units - condition.previous_month_consumption)
                    / condition.previous_month_consumption
                ) * 100
                condition.consumption_variance_percent = variance
            else:
                condition.consumption_variance_percent = 0.0

    def _compute_validation_steps(self):
        """Compute the status of each validation step"""
        for condition in self:
            try:
                condition.step_1_data_imported = condition._check_step_1_data_imported()
                condition.step_2_invoice_created = (
                    condition._check_step_2_invoice_created()
                )
                condition.step_3_payment_processed = (
                    condition._check_step_3_payment_processed()
                )
                condition.step_4_bank_reconciled = (
                    condition._check_step_4_bank_reconciled()
                )
                condition.step_5_invoice_reconciled = (
                    condition._check_step_5_invoice_reconciled()
                )
                condition.step_6_notification_sent = (
                    condition._check_step_6_notification_sent()
                )
            except Exception:
                condition.step_1_data_imported = False
                condition.step_2_invoice_created = False
                condition.step_3_payment_processed = False
                condition.step_4_bank_reconciled = False
                condition.step_5_invoice_reconciled = False
                condition.step_6_notification_sent = False

    def _check_step_1_data_imported(self):
        """Check if water usage data has been imported for the month"""
        if not self.year or not self.month:
            return False

        if "water.usage" not in self.env:
            return False

        water_usage = self.env["water.usage"].search(
            [
                ("year", "=", self.year),
                ("month", "=", self.month),
                ("consumption_units", ">", 0),
            ],
            limit=1,
        )

        if water_usage:
            self.consumption_units = water_usage.consumption_units
            return True
        return False

    def _invoice_domain(self, start_date, end_date):
        """Base domain for water bill invoice searches"""
        domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("amount_total", ">=", self.minimum_amount),
        ]
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        return domain

    def _check_step_2_invoice_created(self):
        """Check if invoice exists with proper amount and attachment"""
        if not self.year or not self.month:
            return False
        start_date, end_date = self._get_month_date_range()
        invoices = self.env["account.move"].search(
            self._invoice_domain(start_date, end_date)
        )
        return any(inv.attachment_ids for inv in invoices)

    def _find_month_invoices(self):
        """Find posted invoices for the month with attachments"""
        if not self.year or not self.month:
            return self.env["account.move"]
        start_date, end_date = self._get_month_date_range()
        return (
            self.env["account.move"]
            .search(self._invoice_domain(start_date, end_date))
            .filtered(lambda m: m.attachment_ids)
        )

    def _check_step_3_payment_processed(self):
        """Check if payment has been processed with attachment"""
        invoices = self._find_month_invoices()
        if not invoices:
            return False

        for invoice in invoices:
            payments = invoice._get_reconciled_payments()
            for payment in payments:
                if payment.attachment_ids:
                    return True
        return False

    def _check_step_4_bank_reconciled(self):
        """Check if bank statement has been reconciled"""
        invoices = self._find_month_invoices()
        if not invoices:
            return False

        for invoice in invoices:
            payments = invoice._get_reconciled_payments()
            for payment in payments:
                if payment.is_reconciled:
                    return True
        return False

    def _check_step_5_invoice_reconciled(self):
        """Check if invoice is fully reconciled"""
        invoices = self._find_month_invoices()
        if not invoices:
            return False

        return any(inv.payment_state == "paid" for inv in invoices)

    def _check_step_6_notification_sent(self):
        """Check if notification has been sent to communication channel"""
        if not self.year or not self.month:
            return False
        start_date, end_date = self._get_month_date_range()
        invoices = self.env["account.move"].search(
            self._invoice_domain(start_date, end_date)
        )
        for invoice in invoices:
            messages = self.env["mail.message"].search(
                [
                    ("res_id", "=", invoice.id),
                    ("model", "=", "account.move"),
                    ("body", "ilike", "water"),
                    ("message_type", "=", "notification"),
                ]
            )
            if messages:
                return True
        return False

    def _get_month_date_range(self):
        """Get start and end dates for the condition's month"""
        if not self.year or not self.month:
            return None, None

        start_date = fields.Date.from_string(f"{self.year}-{self.month:02d}-01")
        last_day = calendar.monthrange(self.year, self.month)[1]
        end_date = fields.Date.from_string(f"{self.year}-{self.month:02d}-{last_day}")

        return start_date, end_date

    def _compute_condition_state(self):
        """Compute overall condition state based on validation steps"""
        for condition in self:
            if condition.error_count > 0:
                condition.condition_state = "incomplete"
            elif condition.warning_count > 0:
                condition.condition_state = "warnings"
            elif all(
                [
                    condition.step_1_data_imported,
                    condition.step_2_invoice_created,
                    condition.step_3_payment_processed,
                    condition.step_4_bank_reconciled,
                    condition.step_5_invoice_reconciled,
                    condition.step_6_notification_sent,
                ]
            ):
                condition.condition_state = "complete"
            else:
                condition.condition_state = "incomplete"

    def _run_validation_checks(self):
        """Run all validation checks and return results"""
        results = []

        if self.step_1_data_imported:
            results.append(
                {
                    "check_name": "Water Usage Data Import",
                    "status": "success",
                    "message": f"Water usage data imported for {self.year}/{self.month:02d}",
                    "details": f"Consumption: {self.consumption_units} units",
                }
            )
        else:
            results.append(
                {
                    "check_name": "Water Usage Data Import",
                    "status": "error",
                    "message": f"No water usage data found for {self.year}/{self.month:02d}",
                    "details": "Please import water usage data with positive consumption",
                }
            )

        if self.step_1_data_imported and self.previous_month_consumption > 0:
            if (
                abs(self.consumption_variance_percent)
                > self.maximum_consumption_variance
            ):
                results.append(
                    {
                        "check_name": "Consumption Variance Analysis",
                        "status": "warning",
                        "message": f"High consumption variance: {self.consumption_variance_percent:.1f}%",
                        "details": f"Current: {self.consumption_units}, Previous: {self.previous_month_consumption}",
                    }
                )
            else:
                results.append(
                    {
                        "check_name": "Consumption Variance Analysis",
                        "status": "success",
                        "message": f"Consumption variance within limits: {self.consumption_variance_percent:.1f}%",
                        "details": f"Current: {self.consumption_units}, Previous: {self.previous_month_consumption}",
                    }
                )

        invoices = self._find_month_invoices()
        if self.step_2_invoice_created:
            invoice_names = ", ".join(invoices.mapped("name")) if invoices else "Found"
            results.append(
                {
                    "check_name": "Invoice Creation",
                    "status": "success",
                    "message": f"Invoice(s) created: {invoice_names}",
                    "details": f"Attachments: {sum(len(inv.attachment_ids) for inv in invoices)}",
                }
            )
        else:
            results.append(
                {
                    "check_name": "Invoice Creation",
                    "status": "error",
                    "message": "No valid water bill invoice found for this month",
                    "details": f"Expected posted invoice >= {self.minimum_amount} with attachment",
                }
            )

        if self.step_3_payment_processed:
            results.append(
                {
                    "check_name": "Payment Processing",
                    "status": "success",
                    "message": "Payment processed with attachment",
                }
            )
        else:
            results.append(
                {
                    "check_name": "Payment Processing",
                    "status": "error",
                    "message": "No payment with attachment found",
                    "details": "Payment must have supporting attachment",
                }
            )

        if self.step_4_bank_reconciled:
            results.append(
                {
                    "check_name": "Bank Reconciliation",
                    "status": "success",
                    "message": "Payment reconciled with bank statement",
                }
            )
        else:
            results.append(
                {
                    "check_name": "Bank Reconciliation",
                    "status": "error",
                    "message": "Payment not reconciled with bank statement",
                }
            )

        if self.step_5_invoice_reconciled:
            results.append(
                {
                    "check_name": "Invoice Reconciliation",
                    "status": "success",
                    "message": "Invoice fully paid and reconciled",
                }
            )
        else:
            results.append(
                {
                    "check_name": "Invoice Reconciliation",
                    "status": "error",
                    "message": "Invoice not fully reconciled",
                }
            )

        if self.step_6_notification_sent:
            results.append(
                {
                    "check_name": "Notification Sent",
                    "status": "success",
                    "message": "Summary posted to communication channel",
                }
            )
        else:
            results.append(
                {
                    "check_name": "Notification Sent",
                    "status": "warning",
                    "message": "No notification found in communication channel",
                    "details": "Consider posting summary to #payments channel",
                }
            )

        return results

    @api.model
    def create_for_checklist(self, checklist_id, year, month):
        """Factory method to create water bill compliance condition"""
        return self.create(
            {
                "name": f"Water Bills - {year}/{month:02d}",
                "description": "Complete water bill payment process validation",
                "checklist_id": checklist_id,
                "year": year,
                "month": month,
                "sequence": 20,
            }
        )
