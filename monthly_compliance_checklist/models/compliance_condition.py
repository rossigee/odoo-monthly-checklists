# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ComplianceCondition(models.AbstractModel):
    """
    Abstract model for compliance conditions that require tier validation.

    This model provides the foundation for all compliance conditions that need
    to be validated through a multi-tier approval process. Each compliance
    condition represents a business process that must be completed monthly.

    Examples:
    - Electric bill compliance (data import → invoice → payment → reconciliation)
    - Rent payment compliance
    - Payroll processing compliance
    """

    _name = "compliance.condition.abstract"
    _description = "Abstract Compliance Condition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc, month desc, sequence, name"

    # Basic identification
    name = fields.Char(
        string="Condition Name",
        required=True,
        tracking=True,
        help="Name of this compliance condition",
    )
    description = fields.Text(
        string="Description",
        help="Detailed description of what this condition validates",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order of execution within the monthly checklist",
    )

    # Time period tracking
    year = fields.Integer(
        string="Year",
        required=True,
        tracking=True,
        help="Year this condition applies to",
    )
    month = fields.Integer(
        string="Month",
        required=True,
        tracking=True,
        help="Month this condition applies to (1-12)",
    )

    # Compliance checklist relationship
    checklist_id = fields.Many2one(
        "monthly.checklist",
        string="Monthly Checklist",
        required=True,
        ondelete="cascade",
        help="The monthly checklist this condition belongs to",
    )

    # Condition state and validation
    condition_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("incomplete", "Incomplete"),
            ("warnings", "Has Warnings"),
            ("complete", "Complete"),
            ("validated", "Validated"),
            ("failed", "Failed"),
        ],
        string="Condition State",
        default="draft",
        tracking=True,
    )

    # Tier validation configuration (temporarily disabled)
    # _state_from = ['draft', 'incomplete', 'warnings', 'complete']
    # _state_to = ['validated']
    # _tier_validation_manual_config = False

    # Validation tracking
    last_validation_date = fields.Datetime(
        string="Last Validation", help="When this condition was last validated"
    )
    validation_notes = fields.Html(
        string="Validation Notes", help="Notes from the validation process"
    )

    # Warning and error tracking
    warning_count = fields.Integer(
        string="Warning Count",
        compute="_compute_validation_status",
        store=True,
        help="Number of non-blocking validation warnings",
    )
    error_count = fields.Integer(
        string="Error Count",
        compute="_compute_validation_status",
        store=True,
        help="Number of blocking validation errors",
    )

    # Validation details (temporarily disabled)
    # validation_details = fields.One2many(
    #     'compliance.validation.detail',
    #     'condition_id',
    #     string='Validation Details',
    #     help='Detailed validation results and messages'
    # )

    # Temporarily simplified validation status computation
    def _compute_validation_status(self):
        """Compute warning and error counts (simplified)"""
        for condition in self:
            # Set to zero until validation details are re-enabled
            condition.warning_count = 0
            condition.error_count = 0

    # @api.model
    # def _get_under_validation_exceptions(self):
    #     """Define fields that can be modified during validation"""
    #     return ['validation_notes', 'condition_state']

    def _compute_condition_state(self):
        """
        Abstract method to compute condition state.
        Must be implemented by concrete models.
        """
        raise NotImplementedError("Subclasses must implement _compute_condition_state")

    def validate_condition(self):
        """
        Run validation checks for this condition.
        Simplified version without validation details.
        """
        self.ensure_one()

        # Recompute step flags before building results
        if hasattr(self, "_compute_validation_steps"):
            self._compute_validation_steps()

        # Run condition-specific validation
        validation_results = self._run_validation_checks()

        # Update condition state based on results
        self._compute_condition_state()

        # Update validation timestamp
        self.last_validation_date = fields.Datetime.now()

        return validation_results

    def _run_validation_checks(self):
        """
        Abstract method to run validation checks.
        Must be implemented by concrete models.

        Returns: List of dicts with keys:
        - check_name: Name of the validation check
        - status: 'success', 'warning', or 'error'
        - message: Human-readable message
        - details: Optional detailed information
        """
        raise NotImplementedError("Subclasses must implement _run_validation_checks")

    def action_validate_condition(self):
        """Button action to manually trigger validation"""
        self.validate_condition()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Validation Complete",
                "message": f"Condition validation completed with {self.warning_count} warnings and {self.error_count} errors",
                "type": "info" if self.error_count == 0 else "warning",
            },
        }

    def action_view_validation_details(self):
        """Open validation details view (temporarily disabled)"""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Feature Temporarily Disabled",
                "message": "Validation details view is temporarily disabled during development",
                "type": "info",
            },
        }

    def request_validation(self):
        """Request validation (tier validation temporarily disabled)"""
        # Run validation checks first
        self.validate_condition()

        # Simple state change without tier validation
        if self.error_count == 0:
            self.condition_state = "validated"
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Validation Requested",
                    "message": "Condition validated successfully",
                    "type": "success",
                },
            }
        else:
            raise UserError(
                f"Cannot request validation: {self.error_count} blocking errors found. "
                "Please resolve all errors before requesting validation."
            )


# Temporarily disabled validation detail model due to abstract model reference issues
# class ComplianceValidationDetail(models.Model):
#     """
#     Detailed validation results for compliance conditions.
#     Stores individual validation check results.
#     """
#     _name = 'compliance.validation.detail'
#     _description = 'Compliance Validation Detail'
#     _order = 'condition_id, sequence, check_name'
#
#     condition_id = fields.Many2one(
#         'compliance.condition.abstract',
#         string='Condition',
#         required=True,
#         ondelete='cascade'
#     )
#     sequence = fields.Integer(string='Sequence', default=10)
#     check_name = fields.Char(string='Check Name', required=True)
#     status = fields.Selection([
#         ('success', 'Success'),
#         ('warning', 'Warning'),
#         ('error', 'Error')
#     ], string='Status', required=True)
#     message = fields.Text(string='Message', required=True)
#     details = fields.Html(string='Details')
#     created_date = fields.Datetime(string='Created', default=fields.Datetime.now)
