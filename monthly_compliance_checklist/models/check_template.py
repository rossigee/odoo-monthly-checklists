# -*- coding: utf-8 -*-

import calendar
from datetime import date

from odoo import api, fields, models


class CheckTemplate(models.Model):
    """
    Check Template - defines a compliance check that may apply to certain months
    Each template can generate check instances for applicable months
    """

    _name = "check.template"
    _description = "Check Template"
    _order = "sequence, name"

    name = fields.Char(string="Check Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    # Dynamic template types from registered compliance check models
    def _get_template_types(self):
        """Get available template types from registered compliance check models"""
        try:
            from .abstract_compliance_check import AbstractComplianceCheck

            return AbstractComplianceCheck.get_registered_check_types(self.env)
        except Exception:
            # Fallback during module installation
            return [
                ("partner_payment", "Partner Payment Check"),
                ("attachment_check", "Attachment Requirements"),
            ]

    template_type = fields.Selection(
        selection="_get_template_types",
        string="Template Type",
        required=True,
        default="partner_payment",
    )

    # Reference to the actual compliance check record
    compliance_check_id = fields.Reference(
        selection="_get_compliance_check_models",
        string="Compliance Check",
        help="The actual compliance check configuration",
    )

    # Human-readable condition summary from the related compliance check
    condition_summary = fields.Text(
        string="Condition Summary",
        compute="_compute_condition_summary",
        help="Human-readable description of the compliance check condition",
    )

    def _get_compliance_check_models(self):
        """Get available compliance check models for Reference field"""
        models = []
        for model_name in self.env.registry:
            model_class = self.env.registry[model_name]
            if hasattr(model_class, "_compliance_check_type"):
                models.append((model_name, model_class._compliance_check_name))
        return models

    @api.depends("compliance_check_id")
    def _compute_condition_summary(self):
        """Get condition summary from the related compliance check"""
        for record in self:
            if record.compliance_check_id and hasattr(
                record.compliance_check_id, "condition_summary"
            ):
                record.condition_summary = record.compliance_check_id.condition_summary
            else:
                record.condition_summary = "No configuration details available"

    # === PARTNER PAYMENT CHECK FIELDS ===
    partner_id = fields.Many2one(
        "res.partner",
        string="Required Partner",
        help="Specific partner that must have transactions",
    )
    bill_identifier = fields.Char(
        string="Bill Identifier",
        help="Descriptive name for the bill type, e.g., House 349/1",
    )
    min_amount = fields.Float(
        string="Minimum Amount", help="Minimum payment amount for this check"
    )
    max_amount = fields.Float(
        string="Maximum Amount", help="Maximum payment amount for this check"
    )
    expected_amount = fields.Float(
        string="Expected Amount",
        help="Expected transaction amount (legacy, use min/max for ranges)",
    )
    amount_tolerance = fields.Float(
        string="Amount Tolerance %",
        default=0.0,
        help="Allowed variance percentage (e.g., 5 for ±5%)",
    )
    payment_frequency = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("annually", "Annually"),
            ("weekly", "Weekly"),
        ],
        string="Payment Frequency",
        default="monthly",
    )
    require_reconciliation = fields.Boolean(
        string="Must be Reconciled", help="Payment must be reconciled/paid"
    )

    # === ATTACHMENT CHECK FIELDS ===
    attachment_types = fields.Selection(
        [
            ("pdf", "PDF Documents"),
            ("image", "Images (PNG, JPG)"),
            ("excel", "Excel/CSV Files"),
            ("any", "Any File Type"),
        ],
        string="Required File Types",
        default="pdf",
    )
    min_attachments = fields.Integer(
        string="Minimum Attachments",
        default=1,
        help="Minimum number of required attachments",
    )
    max_attachments = fields.Integer(
        string="Maximum Attachments", help="Maximum allowed attachments (0 = unlimited)"
    )
    filename_pattern = fields.Char(
        string="Filename Pattern",
        help='Regex pattern for filename validation (e.g., "invoice.*\\.pdf")',
    )
    min_filesize_kb = fields.Integer(
        string="Minimum File Size (KB)", help="Minimum file size in kilobytes"
    )
    max_filesize_kb = fields.Integer(
        string="Maximum File Size (KB)", help="Maximum file size in kilobytes"
    )

    # === RECURRING EXPENSE CHECK FIELDS ===
    expense_category = fields.Selection(
        [
            ("rent", "Rent/Lease"),
            ("utilities", "Utilities"),
            ("insurance", "Insurance"),
            ("subscriptions", "Subscriptions"),
            ("maintenance", "Maintenance"),
            ("other", "Other Recurring"),
        ],
        string="Expense Category",
        default="utilities",
    )
    account_ids = fields.Many2many(
        "account.account",
        string="Expense Accounts",
        help="Accounts to monitor for this expense",
    )
    expected_range_min = fields.Float(
        string="Expected Min Amount", help="Minimum expected amount for this expense"
    )
    expected_range_max = fields.Float(
        string="Expected Max Amount", help="Maximum expected amount for this expense"
    )
    variance_alert = fields.Boolean(
        string="Alert on Variance",
        default=True,
        help="Flag when amount is outside expected range",
    )
    supplier_validation = fields.Boolean(
        string="Validate Supplier", help="Check against approved vendor list"
    )
    approved_partners = fields.Many2many(
        "res.partner",
        "template_approved_partner_rel",
        string="Approved Suppliers",
        help="List of approved suppliers for this expense",
    )

    # === ACCOUNT BALANCE CHECK FIELDS ===
    balance_type = fields.Selection(
        [
            ("debit", "Debit Balance"),
            ("credit", "Credit Balance"),
            ("zero", "Zero Balance"),
            ("range", "Balance Range"),
        ],
        string="Balance Type",
        default="range",
    )
    target_balance = fields.Float(
        string="Target Balance", help="Expected account balance"
    )
    balance_tolerance = fields.Float(
        string="Balance Tolerance", help="Allowed variance from target balance"
    )

    # === TRANSACTION COUNT CHECK FIELDS ===
    min_transaction_count = fields.Integer(
        string="Minimum Transactions",
        default=1,
        help="Minimum number of transactions required",
    )
    max_transaction_count = fields.Integer(
        string="Maximum Transactions",
        help="Maximum number of transactions allowed (0 = unlimited)",
    )
    count_filter_partner = fields.Many2one(
        "res.partner",
        string="Filter by Partner",
        help="Count only transactions with this partner",
    )
    count_filter_amount_min = fields.Float(
        string="Min Amount Filter", help="Count only transactions above this amount"
    )

    # === AMOUNT THRESHOLD CHECK FIELDS ===
    threshold_amount = fields.Float(
        string="Threshold Amount", help="Amount threshold to check against"
    )
    threshold_operator = fields.Selection(
        [
            (">=", "Greater than or equal"),
            (">", "Greater than"),
            ("<=", "Less than or equal"),
            ("<", "Less than"),
            ("=", "Exactly equal"),
        ],
        string="Threshold Operator",
        default=">=",
    )
    aggregate_function = fields.Selection(
        [
            ("sum", "Sum of all transactions"),
            ("max", "Maximum single transaction"),
            ("min", "Minimum single transaction"),
            ("avg", "Average transaction amount"),
        ],
        string="Aggregate Function",
        default="sum",
    )

    # === CUSTOM DOMAIN CHECK FIELDS ===
    custom_domain = fields.Text(
        string="Custom Domain Filter", help="Advanced: Python domain filter as text"
    )
    custom_description = fields.Text(
        string="Custom Check Description",
        help="Description of what this custom check validates",
    )

    # Validity period
    valid_from = fields.Date(
        string="Valid From",
        help="Date when this check becomes effective (leave empty for no start limit)",
    )
    valid_until = fields.Date(
        string="Valid Until",
        help="Date when this check expires (leave empty for perpetual)",
    )

    def is_applicable_for_month(self, year, month):
        """
        Determine if this check template should create a check instance
        for the given month/year
        """
        # Get the first day of the month to check
        check_date = date(year, month, 1)

        # Check start date
        if self.valid_from and check_date < self.valid_from:
            return False

        # Check end date
        if self.valid_until and check_date > self.valid_until:
            return False

        return True

    def evaluate_condition(self, year, month, instance=None):
        """
        Evaluate if this template's conditions are met for the given month/year
        Returns: (is_met: bool, details: dict)
        """
        if self.compliance_check_id:
            # Use the referenced compliance check record (legacy models don't accept instance)
            return self.compliance_check_id.evaluate_condition(year, month)
        else:
            # Fallback to legacy evaluation for backward compatibility
            return self._evaluate_legacy_condition(year, month, instance=instance)

    def _evaluate_legacy_condition(self, year, month, instance=None):
        """Legacy evaluation method for backward compatibility"""
        # For partner_payment type, use the specific method
        if self.template_type == "partner_payment":
            start_date, end_date = self._get_month_date_range(year, month)
            return self._evaluate_partner_payment(start_date, end_date, instance)
        # This can be removed once all templates are migrated to use compliance_check_id
        return False, {"message": "No compliance check configuration found"}

    @api.model
    def get_dynamic_form_view(self, template_type):
        """
        Get dynamic form view content for the specified template type.
        Used by the template form to show appropriate configuration fields.
        """
        renderer = self.env["compliance.view.renderer"]
        return renderer.get_check_type_view(template_type, "form")

    @api.onchange("template_type")
    def _onchange_template_type(self):
        """Clear compliance check reference when template type changes"""
        if self.template_type:
            self.compliance_check_id = False

    def action_create_compliance_check(self):
        """Create a new compliance check record of the selected type"""
        if not self.template_type:
            return

        # Find the model for this check type
        check_model = None
        for model_name in self.env.registry:
            model_class = self.env.registry[model_name]
            if (
                hasattr(model_class, "_compliance_check_type")
                and model_class._compliance_check_type == self.template_type
            ):
                check_model = model_name
                break

        if not check_model:
            return

        # Get the model instance to call its configuration action
        model_instance = self.env[check_model]
        action = model_instance.get_configuration_action()

        # Add context to link back to this template after creation
        action["context"] = dict(
            action.get("context", {}),
            **{
                "default_name": self.name or "New Check",
                "default_sequence": self.sequence,
                "default_valid_from": self.valid_from,
                "default_valid_until": self.valid_until,
                "template_id": self.id,
            },
        )

        return action

    def action_edit_compliance_check(self):
        """Open the compliance check record for editing"""
        if not self.compliance_check_id:
            return

        return {
            "type": "ir.actions.act_window",
            "name": f"Edit {self.compliance_check_id._compliance_check_name}",
            "res_model": self.compliance_check_id._name,
            "res_id": self.compliance_check_id.id,
            "view_mode": "form",
            "target": "new",
        }

    def _evaluate_partner_payment(self, start_date, end_date, instance=None):
        """Evaluate partner payment check"""
        if not self.partner_id:
            return False, {"message": "No partner specified for payment check"}

        # Find posted payment lines with the required partner
        domain = [
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("partner_id", "=", self.partner_id.id),
            ("credit", ">", 0),  # Payments are credits
            ("parent_state", "=", "posted"),
        ]

        # Apply amount range if specified
        if self.min_amount:
            domain.append(("credit", ">=", self.min_amount))
        if self.max_amount:
            domain.append(("credit", "<=", self.max_amount))
        elif self.expected_amount > 0:  # Legacy support
            tolerance = (
                self.expected_amount * (self.amount_tolerance / 100)
                if self.amount_tolerance
                else 0
            )
            min_amt = self.expected_amount - tolerance
            max_amt = self.expected_amount + tolerance
            domain.extend([("credit", ">=", min_amt), ("credit", "<=", max_amt)])

        move_lines = self.env["account.move.line"].search(domain)

        if not move_lines:
            range_desc = (
                f" between {self.min_amount} and {self.max_amount}"
                if self.min_amount or self.max_amount
                else (
                    f" around {self.expected_amount} (±{self.amount_tolerance}%)"
                    if self.expected_amount
                    else ""
                )
            )
            return False, {
                "message": f"No payments found for partner {self.partner_id.name}{range_desc}"
            }

        # Filter out lines already matched to other instances
        if instance:
            matched_line_ids = (
                self.env["check.instance"]
                .search(
                    [("id", "!=", instance.id), ("matched_move_line_id", "!=", False)]
                )
                .mapped("matched_move_line_id.id")
            )
            available_lines = move_lines.filtered(
                lambda line: line.id not in matched_line_ids
            )
        else:
            available_lines = move_lines

        if not available_lines:
            return False, {
                "message": f"All matching payments for {self.partner_id.name} are already used by other checks"
            }

        # Select the best match (e.g., most recent)
        selected_line = available_lines.sorted(
            key=lambda line: line.date, reverse=True
        )[0]

        # Link to instance if provided
        if instance:
            instance.matched_move_line_id = selected_line

        # Check reconciliation if required (on the move)
        if self.require_reconciliation:
            move = selected_line.move_id
            if move.payment_state != "paid":
                return False, {
                    "message": f"Payment found for {self.partner_id.name} but not reconciled (ID: {selected_line.id})"
                }

        move_ids = list(set(line.move_id.id for line in available_lines))

        return True, {
            "message": f"Partner payment check passed: Payment {selected_line.id} ({selected_line.credit}) linked for {self.partner_id.name}",
            "move_count": len(move_ids),
            "total_amount": sum(m.credit for m in available_lines),
            "move_ids": move_ids,
            "matched_line_id": selected_line.id,
        }

    def _evaluate_attachment_check(self, start_date, end_date):
        """Evaluate attachment requirements check"""
        # Get base transactions for the period
        moves = self.env["account.move"].search(
            [
                ("date", ">=", start_date),
                ("date", "<=", end_date),
                ("state", "=", "posted"),
            ]
        )

        if not moves:
            return False, {"message": "No transactions found for this period"}

        import re

        matching_moves = []

        for move in moves:
            if not move.attachment_ids:
                continue

            attachments = move.attachment_ids

            # Filter by file type if specified
            if self.attachment_types != "any":
                if self.attachment_types == "pdf":
                    attachments = attachments.filtered(
                        lambda a: a.mimetype == "application/pdf"
                    )
                elif self.attachment_types == "image":
                    attachments = attachments.filtered(
                        lambda a: a.mimetype.startswith("image/")
                    )
                elif self.attachment_types == "excel":
                    attachments = attachments.filtered(
                        lambda a: a.mimetype
                        in [
                            "application/vnd.ms-excel",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "text/csv",
                        ]
                    )

            # Check attachment count
            if len(attachments) < self.min_attachments:
                continue
            if self.max_attachments > 0 and len(attachments) > self.max_attachments:
                continue

            # Check filename pattern if specified
            if self.filename_pattern:
                pattern_matches = any(
                    re.search(self.filename_pattern, attachment.name or "")
                    for attachment in attachments
                )
                if not pattern_matches:
                    continue

            # Check file sizes if specified
            if self.min_filesize_kb or self.max_filesize_kb:
                size_valid = True
                for attachment in attachments:
                    size_kb = (attachment.file_size or 0) / 1024
                    if self.min_filesize_kb and size_kb < self.min_filesize_kb:
                        size_valid = False
                        break
                    if self.max_filesize_kb and size_kb > self.max_filesize_kb:
                        size_valid = False
                        break
                if not size_valid:
                    continue

            matching_moves.append(move)

        if not matching_moves:
            return False, {
                "message": "No transactions found meeting attachment requirements"
            }

        return True, {
            "message": f"Attachment check passed: {len(matching_moves)} transaction(s) with valid attachments",
            "move_count": len(matching_moves),
            "move_ids": [m.id for m in matching_moves],
        }

    def _evaluate_recurring_expense(self, start_date, end_date):
        """Evaluate recurring expense check"""
        if not self.account_ids:
            return False, {"message": "No expense accounts specified"}

        # Find transactions in specified expense accounts
        domain = [
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("state", "=", "posted"),
            ("line_ids.account_id", "in", self.account_ids.ids),
        ]

        moves = self.env["account.move"].search(domain)

        if not moves:
            return False, {
                "message": f"No transactions found in expense accounts for {self.expense_category}"
            }

        # Filter by approved suppliers if validation enabled
        if self.supplier_validation and self.approved_partners:
            approved_moves = moves.filtered(
                lambda m: m.partner_id in self.approved_partners
            )
            if not approved_moves:
                return False, {
                    "message": f"No transactions found from approved suppliers for {self.expense_category}"
                }
            moves = approved_moves

        # Check amount ranges if specified
        if self.expected_range_min or self.expected_range_max:
            total_amount = sum(abs(m.amount_total) for m in moves)

            if self.expected_range_min and total_amount < self.expected_range_min:
                message = f"Expense amount {total_amount} below expected minimum {self.expected_range_min}"
                return not self.variance_alert, {
                    "message": message,
                    "move_ids": moves.ids,
                }

            if self.expected_range_max and total_amount > self.expected_range_max:
                message = f"Expense amount {total_amount} above expected maximum {self.expected_range_max}"
                return not self.variance_alert, {
                    "message": message,
                    "move_ids": moves.ids,
                }

        return True, {
            "message": f"Recurring expense check passed: {self.expense_category} expenses found",
            "move_count": len(moves),
            "total_amount": sum(abs(m.amount_total) for m in moves),
            "move_ids": moves.ids,
        }

    def _evaluate_account_balance(self, start_date, end_date):
        """Evaluate account balance check"""
        if not self.account_ids:
            return False, {"message": "No accounts specified for balance check"}

        # Calculate account balances as of end_date
        balances = {}
        for account in self.account_ids:
            balance = account.with_context(date=end_date).balance
            balances[account.id] = balance

        total_balance = sum(balances.values())

        if self.balance_type == "zero":
            is_met = abs(total_balance) <= (self.balance_tolerance or 0)
            message = f'Balance {total_balance} {"within" if is_met else "outside"} zero tolerance'
        elif self.balance_type == "debit":
            is_met = total_balance > 0
            message = f'Balance {total_balance} {"is" if is_met else "is not"} a debit balance'
        elif self.balance_type == "credit":
            is_met = total_balance < 0
            message = f'Balance {total_balance} {"is" if is_met else "is not"} a credit balance'
        elif self.balance_type == "range":
            tolerance = self.balance_tolerance or 0
            is_met = abs(total_balance - self.target_balance) <= tolerance
            message = f'Balance {total_balance} {"within" if is_met else "outside"} target {self.target_balance} ±{tolerance}'
        else:
            is_met = False
            message = "Unknown balance type specified"

        return is_met, {
            "message": message,
            "balance": total_balance,
            "account_balances": balances,
        }

    def _evaluate_transaction_count(self, start_date, end_date):
        """Evaluate transaction count check"""
        domain = [
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("state", "=", "posted"),
        ]

        # Add optional filters
        if self.count_filter_partner:
            domain.append(("partner_id", "=", self.count_filter_partner.id))
        if self.count_filter_amount_min:
            domain.append(("amount_total", ">=", self.count_filter_amount_min))
        if self.account_ids:
            domain.append(("line_ids.account_id", "in", self.account_ids.ids))

        moves = self.env["account.move"].search(domain)
        count = len(moves)

        # Check count requirements
        is_met = count >= self.min_transaction_count
        if self.max_transaction_count > 0:
            is_met = is_met and count <= self.max_transaction_count

        message = f"Found {count} transactions"
        if not is_met:
            if count < self.min_transaction_count:
                message += f" (need at least {self.min_transaction_count})"
            elif self.max_transaction_count > 0 and count > self.max_transaction_count:
                message += f" (maximum allowed: {self.max_transaction_count})"

        return is_met, {
            "message": message,
            "transaction_count": count,
            "move_ids": moves.ids,
        }

    def _evaluate_amount_threshold(self, start_date, end_date):
        """Evaluate amount threshold check"""
        domain = [
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("state", "=", "posted"),
        ]

        if self.account_ids:
            domain.append(("line_ids.account_id", "in", self.account_ids.ids))
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))

        moves = self.env["account.move"].search(domain)

        if not moves:
            return False, {"message": "No transactions found for threshold check"}

        # Calculate aggregate value
        amounts = [abs(m.amount_total) for m in moves]

        if self.aggregate_function == "sum":
            aggregate_value = sum(amounts)
        elif self.aggregate_function == "max":
            aggregate_value = max(amounts)
        elif self.aggregate_function == "min":
            aggregate_value = min(amounts)
        elif self.aggregate_function == "avg":
            aggregate_value = sum(amounts) / len(amounts)
        else:
            return False, {
                "message": f"Unknown aggregate function: {self.aggregate_function}"
            }

        # Apply threshold comparison
        if self.threshold_operator == ">=":
            is_met = aggregate_value >= self.threshold_amount
        elif self.threshold_operator == ">":
            is_met = aggregate_value > self.threshold_amount
        elif self.threshold_operator == "<=":
            is_met = aggregate_value <= self.threshold_amount
        elif self.threshold_operator == "<":
            is_met = aggregate_value < self.threshold_amount
        elif self.threshold_operator == "=":
            is_met = aggregate_value == self.threshold_amount
        else:
            return False, {
                "message": f"Unknown threshold operator: {self.threshold_operator}"
            }

        return is_met, {
            "message": f'{self.aggregate_function.title()} amount {aggregate_value} {self.threshold_operator} {self.threshold_amount}: {"PASS" if is_met else "FAIL"}',
            "aggregate_value": aggregate_value,
            "move_count": len(moves),
            "move_ids": moves.ids,
        }

    def _evaluate_custom_domain(self, start_date, end_date):
        """Evaluate custom domain filter"""
        if not self.custom_domain:
            return False, {"message": "No custom domain specified"}

        try:
            import ast

            domain = ast.literal_eval(self.custom_domain)

            # Add date filtering to custom domain
            domain.extend(
                [
                    ("date", ">=", start_date),
                    ("date", "<=", end_date),
                    ("state", "=", "posted"),
                ]
            )

            moves = self.env["account.move"].search(domain)

            return len(moves) > 0, {
                "message": f"Custom domain matched {len(moves)} transaction(s)",
                "move_count": len(moves),
                "move_ids": moves.ids,
                "description": self.custom_description or "Custom domain check",
            }

        except Exception as e:
            return False, {"message": f"Error in custom domain: {str(e)}"}

    def _check_amount_conditions(self, move):
        """Check if move meets amount conditions"""
        amount = abs(move.amount_total)

        if self.minimum_amount and amount < self.minimum_amount:
            return False
        if self.maximum_amount and amount > self.maximum_amount:
            return False

        return True

    def _get_month_date_range(self, year, month):
        """Get start and end dates for the given month"""
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        return start_date, end_date

    def create_check_instance(self, checklist_id):
        """Create a check instance for this template"""
        return self.env["check.instance"].create(
            {
                "name": self.name,
                "template_id": self.id,
                "checklist_id": checklist_id,
                "sequence": self.sequence,
            }
        )
