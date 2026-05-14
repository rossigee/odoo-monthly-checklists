# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ElectricBillCompliance(models.Model):
    """
    Simplified Electric Bill Compliance Condition for testing
    """

    _name = "electric.bill.compliance"
    _inherit = "compliance.condition.abstract"
    _description = "Electric Bill Compliance Condition"

    # Electric bill specific fields (simplified)
    minimum_amount = fields.Float(
        string="Minimum Expected Amount",
        default=50.0,
        help="Minimum expected invoice amount for validation",
    )

    # Simple boolean fields without compute methods
    step_1_data_imported = fields.Boolean("Data Imported", default=False)
    step_2_invoice_created = fields.Boolean("Invoice Created", default=False)
    step_3_payment_processed = fields.Boolean("Payment Processed", default=False)
    step_4_bank_reconciled = fields.Boolean("Bank Reconciled", default=False)
    step_5_invoice_reconciled = fields.Boolean("Invoice Reconciled", default=False)
    step_6_notification_sent = fields.Boolean("Notification Sent", default=False)

    def _compute_condition_state(self):
        """Simplified condition state computation"""
        for condition in self:
            if all(
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
        """Simplified validation checks"""
        return [
            {
                "check_name": "Electric Bill Process",
                "status": "success" if self.condition_state == "complete" else "error",
                "message": "Electric bill process validation",
                "details": "Simplified validation for testing",
            }
        ]

    @api.model
    def create_for_checklist(self, checklist_id, year, month):
        """Factory method to create electric bill compliance condition"""
        return self.create(
            {
                "name": f"Electric Bills - {year}/{month:02d}",
                "description": "Simplified electric bill compliance for testing",
                "checklist_id": checklist_id,
                "year": year,
                "month": month,
                "sequence": 10,
            }
        )
