# -*- coding: utf-8 -*-

from datetime import date

from odoo import fields, models


class ComplianceTemplateItem(models.Model):
    """
    Template items that define automated compliance conditions
    Each item describes conditions that must be met for compliance
    """

    _name = "compliance.template.item"
    _description = "Compliance Template Item"
    _order = "sequence, name"

    name = fields.Char(string="Check Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    template_id = fields.Many2one(
        "compliance.template", string="Template", required=True, ondelete="cascade"
    )

    # Condition definition
    condition_type = fields.Selection(
        [
            ("account_transaction", "Account has Transaction"),
            ("partner_transaction", "Partner has Transaction"),
            ("amount_threshold", "Amount Threshold Met"),
            ("attachment_required", "Transaction has Attachment"),
            ("multi_condition", "Multiple Conditions"),
        ],
        string="Condition Type",
        required=True,
        default="multi_condition",
    )

    # Account/Partner filtering
    account_ids = fields.Many2many(
        "account.account",
        string="Required Accounts",
        help="Accounts that must have transactions",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Required Partners",
        help="Partners that must have transactions",
    )

    # Transaction filtering
    transaction_type = fields.Selection(
        [
            ("income", "Income Only"),
            ("expense", "Expense Only"),
            ("any", "Any Transaction"),
        ],
        string="Transaction Type",
        default="any",
    )

    move_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("in_invoice", "Vendor Bill"),
            ("out_refund", "Customer Credit Note"),
            ("in_refund", "Vendor Credit Note"),
            ("entry", "Journal Entry"),
            ("any", "Any Move Type"),
        ],
        string="Move Type",
        default="any",
    )

    # Amount conditions
    minimum_amount = fields.Float(
        string="Minimum Amount", help="Minimum transaction amount required"
    )
    maximum_amount = fields.Float(
        string="Maximum Amount", help="Maximum transaction amount allowed"
    )

    # Additional conditions
    require_attachment = fields.Boolean(
        string="Require Attachment",
        help="Transaction must have at least one attachment",
    )
    require_reconciliation = fields.Boolean(
        string="Require Reconciliation", help="Transaction must be reconciled"
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

    def evaluate_condition(self, year, month):
        """
        Evaluate if this condition is met for the given month/year
        Returns: (is_met: bool, details: dict)
        """
        # All conditions are now automated - no manual checks

        # Get date range for the month
        start_date, end_date = self._get_month_date_range(year, month)

        # Build domain for account moves
        domain = [
            ("date", ">=", start_date),
            ("date", "<=", end_date),
            ("state", "=", "posted"),
        ]

        # Add account filtering
        if self.account_ids:
            domain.append(("line_ids.account_id", "in", self.account_ids.ids))

        # Add partner filtering
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))

        # Add move type filtering
        if self.move_type != "any":
            domain.append(("move_type", "=", self.move_type))

        # Add transaction type filtering
        if self.transaction_type != "any":
            if self.transaction_type == "income":
                domain.append(
                    (
                        "line_ids.account_id.account_type",
                        "in",
                        ["income", "income_other"],
                    )
                )
            elif self.transaction_type == "expense":
                domain.append(
                    (
                        "line_ids.account_id.account_type",
                        "in",
                        ["expense", "expense_depreciation", "expense_direct_cost"],
                    )
                )

        # Find matching moves
        moves = self.env["account.move"].search(domain)

        if not moves:
            return False, {"message": "No matching transactions found"}

        # Apply amount conditions
        if self.minimum_amount or self.maximum_amount:
            valid_moves = moves.filtered(lambda m: self._check_amount_conditions(m))
            if not valid_moves:
                return False, {"message": "No transactions meet amount requirements"}
            moves = valid_moves

        # Apply attachment requirements
        if self.require_attachment:
            moves_with_attachments = moves.filtered(lambda m: m.attachment_ids)
            if not moves_with_attachments:
                return False, {"message": "No transactions have required attachments"}
            moves = moves_with_attachments

        # Apply reconciliation requirements
        if self.require_reconciliation:
            reconciled_moves = moves.filtered(lambda m: m.payment_state == "paid")
            if not reconciled_moves:
                return False, {"message": "No transactions are reconciled"}
            moves = reconciled_moves

        # Condition is met
        return True, {
            "message": f"Condition satisfied by {len(moves)} transaction(s)",
            "move_count": len(moves),
            "total_amount": sum(moves.mapped("amount_total")),
            "move_ids": moves.ids,
        }

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
        import calendar
        from datetime import date

        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        return start_date, end_date

    def is_valid_for_month(self, year, month):
        """
        Check if this template item should be included in the given month
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


# Update the template model to use template items
class ComplianceTemplate(models.Model):
    _inherit = "compliance.template"

    template_items = fields.One2many(
        "compliance.template.item",
        "template_id",
        string="Template Items",
        help="Define the specific checks that should be created each month",
    )
