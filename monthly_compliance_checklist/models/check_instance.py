# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CheckInstance(models.Model):
    """
    Check Instance - a monthly instance of a check template
    Tracks completion status for a specific month
    """

    _name = "check.instance"
    _description = "Check Instance"
    _inherit = ["mail.thread"]
    _order = "sequence, name"

    name = fields.Char(string="Check Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    # References
    template_id = fields.Many2one(
        "check.template", string="Template", required=True, ondelete="cascade"
    )
    checklist_id = fields.Many2one(
        "monthly.checklist",
        string="Monthly Checklist",
        required=True,
        ondelete="cascade",
    )

    # Time tracking - computed from checklist
    year = fields.Integer(string="Year", related="checklist_id.year", store=True)
    month = fields.Integer(string="Month", related="checklist_id.month", store=True)

    # Status tracking
    is_completed = fields.Boolean(
        string="Completed", compute="_compute_is_completed", store=True
    )
    completion_date = fields.Datetime(string="Completion Date")

    # Validation details
    validation_message = fields.Text(
        string="Validation Details", help="Details about condition evaluation"
    )

    # Payment linking
    matched_move_line_id = fields.Many2one(
        "account.move.line",
        string="Matched Payment",
        help="The specific payment line that satisfies this check",
    )

    # Debug field to show search criteria
    debug_info = fields.Text(
        string="Debug Info",
        compute="_compute_debug_info",
        help="Debug information about search criteria",
    )
    related_move_ids = fields.Many2many(
        "account.move",
        string="Related Moves",
        help="Account moves that satisfy this condition",
    )

    @api.depends("template_id", "year", "month")
    def _compute_is_completed(self):
        """Evaluate completion status using template condition"""
        for instance in self:
            if not instance.template_id:
                instance.is_completed = False
                instance.validation_message = "No template defined"
                continue

            was_completed = instance.is_completed

            # Use template to evaluate condition; _evaluate_partner_payment
            # writes matched_move_line_id as a side effect
            is_met, details = instance.template_id.evaluate_condition(
                instance.year, instance.month, instance=instance
            )

            instance.is_completed = is_met
            instance.validation_message = details.get("message", "")

            # Clear link if the check no longer passes
            if not is_met and instance.matched_move_line_id:
                instance.matched_move_line_id = False

            # Update related moves if provided
            if "move_ids" in details:
                instance.related_move_ids = [(6, 0, details["move_ids"])]

            # Track first completion and clear date on regression
            if is_met and not was_completed:
                instance.completion_date = fields.Datetime.now()
            elif not is_met:
                instance.completion_date = False

    def reevaluate_condition(self):
        """Manually trigger condition re-evaluation"""
        self._compute_is_completed()

    @api.depends("template_id", "year", "month")
    def _compute_debug_info(self):
        """Show debug information about search criteria"""
        for instance in self:
            debug_lines = []
            debug_lines.append(f"=== DEBUG INFO FOR {instance.name} ===")
            debug_lines.append(
                f"Template Type: {instance.template_id.template_type if instance.template_id else 'None'}"
            )
            debug_lines.append(f"Year: {instance.year}")
            debug_lines.append(f"Month: {instance.month}")

            if instance.template_id:
                template = instance.template_id
                debug_lines.append(f"Template ID: {template.id}")

                if template.template_type == "partner_payment":
                    # Check both legacy template fields and compliance check record
                    debug_lines.append(
                        f"Legacy Template Partner: {template.partner_id.name if template.partner_id else 'None'} (ID: {template.partner_id.id if template.partner_id else 'None'})"
                    )
                    debug_lines.append(
                        f"Bill Identifier: {template.bill_identifier or 'None'}"
                    )
                    debug_lines.append(f"Min Amount: {template.min_amount}")
                    debug_lines.append(f"Max Amount: {template.max_amount}")
                    debug_lines.append(f"Expected Amount: {template.expected_amount}")
                    debug_lines.append(
                        f"Amount Tolerance: {template.amount_tolerance}%"
                    )
                    debug_lines.append(
                        f"Require Reconciliation: {template.require_reconciliation}"
                    )

                    # Check compliance check record
                    debug_lines.append(
                        f"Compliance Check ID: {template.compliance_check_id}"
                    )
                    if template.compliance_check_id:
                        check_record = template.compliance_check_id
                        if hasattr(check_record, "partner_id"):
                            debug_lines.append(
                                f"Compliance Check Partner: {check_record.partner_id.name if check_record.partner_id else 'None'} (ID: {check_record.partner_id.id if check_record.partner_id else 'None'})"
                            )
                        else:
                            debug_lines.append(
                                "Compliance Check Partner: No partner_id field found"
                            )
                    else:
                        debug_lines.append("No compliance check record linked")

                    # Test the actual evaluation method
                    if instance.year and instance.month:
                        debug_lines.append("=== TESTING ACTUAL EVALUATION ===")
                        try:
                            is_met, details = template.evaluate_condition(
                                instance.year, instance.month
                            )
                            debug_lines.append(
                                f"Evaluation Result: {'PASS' if is_met else 'FAIL'}"
                            )
                            debug_lines.append(
                                f"Evaluation Message: {details.get('message', 'No message')}"
                            )
                            if "move_count" in details:
                                debug_lines.append(
                                    f"Matching Transactions: {details['move_count']}"
                                )
                            if "total_amount" in details:
                                debug_lines.append(
                                    f"Total Amount: {details['total_amount']}"
                                )
                            if "move_ids" in details:
                                debug_lines.append(
                                    f"Transaction IDs: {details['move_ids'][:5]}{'...' if len(details['move_ids']) > 5 else ''}"
                                )
                        except Exception as e:
                            debug_lines.append(f"Error in evaluation: {e}")

                        # Also show what domain SHOULD be used for partner payment
                        debug_lines.append(
                            "=== EXPECTED DOMAIN FOR PARTNER PAYMENT ==="
                        )
                        import calendar
                        from datetime import date

                        start_date = date(instance.year, instance.month, 1)
                        last_day = calendar.monthrange(instance.year, instance.month)[1]
                        end_date = date(instance.year, instance.month, last_day)

                        debug_lines.append(f"Date Range: {start_date} to {end_date}")

                        expected_domain = [
                            ("date", ">=", start_date),
                            ("date", "<=", end_date),
                            ("state", "=", "posted"),
                        ]

                        # Use the compliance check partner if available
                        if (
                            template.compliance_check_id
                            and hasattr(template.compliance_check_id, "partner_id")
                            and template.compliance_check_id.partner_id
                        ):
                            expected_domain.append(
                                (
                                    "partner_id",
                                    "=",
                                    template.compliance_check_id.partner_id.id,
                                )
                            )
                            debug_lines.append(
                                f"Expected Domain (with partner filter): {expected_domain}"
                            )

                            # Test this domain
                            try:
                                moves = instance.env["account.move"].search(
                                    expected_domain
                                )
                                debug_lines.append(
                                    f"Partner-Filtered Transactions Found: {len(moves)}"
                                )
                                if moves:
                                    for move in moves[:5]:
                                        debug_lines.append(
                                            f"  - {move.name} ({move.date}) - Amount: {move.amount_total} - Partner: {move.partner_id.name if move.partner_id else 'No Partner'}"
                                        )
                                    if len(moves) > 5:
                                        debug_lines.append(
                                            f"  ... and {len(moves) - 5} more"
                                        )
                            except Exception as e:
                                debug_lines.append(f"Error testing partner domain: {e}")
                        else:
                            debug_lines.append("No partner available for filtering")

            instance.debug_info = "\n".join(debug_lines)

    def action_view_related_moves(self):
        """Open related moves"""
        return {
            "name": "Related Transactions",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.related_move_ids.ids)],
            "context": self.env.context,
        }
