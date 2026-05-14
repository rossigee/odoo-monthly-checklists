# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PartnerInvoiceCheck(models.Model):
    """
    Partner Invoice Compliance Check
    Validates that specific partners have created invoices/bills with expected criteria
    """
    _name = 'compliance.check.partner.invoice'
    _description = 'Partner Invoice Check'
    _inherit = 'abstract.compliance.check'
    _table = 'compliance_check_partner_invoice'

    # Registration info for the check type registry
    _compliance_check_type = 'partner_invoice'
    _compliance_check_name = 'Partner Invoice Check'

    # Partner invoice specific fields
    partner_id = fields.Many2one(
        'res.partner',
        string='Required Partner',
        required=True,
        help='Specific partner that must have invoices/bills'
    )

    # Invoice type filter
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoices'),
        ('in_invoice', 'Vendor Bills'),
        ('out_refund', 'Customer Credit Notes'),
        ('in_refund', 'Vendor Credit Notes'),
        ('all', 'All Invoice Types')
    ], string='Invoice Type', default='in_invoice')

    minimum_amount = fields.Float(
        string='Minimum Amount',
        help='Minimum invoice amount required (leave 0 for no minimum)'
    )
    maximum_amount = fields.Float(
        string='Maximum Amount',
        help='Maximum invoice amount allowed (leave 0 for no maximum)'
    )
    require_posted = fields.Boolean(
        string='Must be Posted',
        default=True,
        help='Invoice must be in posted state'
    )
    require_payment = fields.Boolean(
        string='Must be Paid',
        help='Invoice must be fully paid/reconciled'
    )

    # Computed field for human-readable summary
    condition_summary = fields.Text(
        string='Condition Summary',
        compute='_compute_condition_summary',
        help='Human-readable description of this check condition'
    )

    @api.depends('partner_id', 'move_type', 'minimum_amount', 'maximum_amount', 'require_posted', 'require_payment')
    def _compute_condition_summary(self):
        """Generate human-readable summary of the check condition"""
        for record in self:
            if not record.partner_id:
                record.condition_summary = "No partner specified"
                continue

            # Invoice type
            type_map = {
                'out_invoice': 'customer invoices',
                'in_invoice': 'vendor bills',
                'out_refund': 'customer credit notes',
                'in_refund': 'vendor credit notes',
                'all': 'invoices/bills'
            }
            invoice_type = type_map.get(record.move_type, 'invoices')

            parts = [f"Partner '{record.partner_id.name}' must have at least one {invoice_type}"]

            # Add amount conditions
            amount_conditions = []
            if record.minimum_amount > 0:
                amount_conditions.append(f"≥ {record.minimum_amount}")
            if record.maximum_amount > 0:
                amount_conditions.append(f"≤ {record.maximum_amount}")

            if amount_conditions:
                parts.append(f"with amount {' and '.join(amount_conditions)}")

            # Add state requirements
            state_conditions = []
            if record.require_posted:
                state_conditions.append("posted")
            if record.require_payment:
                state_conditions.append("fully paid")

            if state_conditions:
                parts.append(f"that is {' and '.join(state_conditions)}")

            record.condition_summary = " ".join(parts) + "."

    @api.model
    def get_evaluation_fields(self):
        """Return fields relevant for partner invoice evaluation"""
        base_fields = super().get_evaluation_fields()
        return base_fields + [
            'partner_id', 'move_type', 'minimum_amount', 'maximum_amount',
            'require_posted', 'require_payment'
        ]

    @classmethod
    def get_view_ids(cls, env):
        """Return view IDs for this check type"""
        return {
            'form': env.ref('monthly_compliance_checklist.view_partner_invoice_check_form').id,
            'tree': env.ref('monthly_compliance_checklist.view_partner_invoice_check_tree').id,
            'search': env.ref('monthly_compliance_checklist.view_partner_invoice_check_search').id,
            'action': env.ref('monthly_compliance_checklist.action_partner_invoice_check').id,
        }

    @api.model
    def get_configuration_action(self):
        """Return action to open this check type's configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partner Invoice Check Configuration',
            'res_model': self._name,
            'view_mode': 'form',
            'view_id': self.env.ref('monthly_compliance_checklist.view_partner_invoice_check_form').id,
            'target': 'new',
            'context': {'default_name': 'New Partner Invoice Check'}
        }

    def evaluate_condition(self, year, month):
        """
        Evaluate partner invoice check for the given month/year.
        Returns: (is_met: bool, details: dict)
        """
        start_date, end_date = self._get_month_date_range(year, month)

        if not self.partner_id:
            return False, {'message': 'No partner specified for invoice check'}

        # Build domain for invoice/bill records
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('partner_id', '=', self.partner_id.id)
        ]

        # Filter by move type
        if self.move_type != 'all':
            domain.append(('move_type', '=', self.move_type))
        else:
            domain.append(('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']))

        # Filter by state if required
        if self.require_posted:
            domain.append(('state', '=', 'posted'))

        moves = self.env['account.move'].search(domain)

        if not moves:
            return False, {'message': f'No invoices found for partner {self.partner_id.name}'}

        # Check amount ranges if specified
        if self.minimum_amount > 0 or self.maximum_amount > 0:
            matching_moves = []
            for move in moves:
                amount = abs(move.amount_total)

                # Check minimum amount
                if self.minimum_amount > 0 and amount < self.minimum_amount:
                    continue

                # Check maximum amount
                if self.maximum_amount > 0 and amount > self.maximum_amount:
                    continue

                matching_moves.append(move)

            if not matching_moves:
                amount_criteria = []
                if self.minimum_amount > 0:
                    amount_criteria.append(f'≥ {self.minimum_amount}')
                if self.maximum_amount > 0:
                    amount_criteria.append(f'≤ {self.maximum_amount}')
                amount_text = ' and '.join(amount_criteria)

                return False, {
                    'message': f'No invoices found for {self.partner_id.name} with amount {amount_text}',
                    'move_ids': moves.ids,
                    'found_amounts': moves.mapped('amount_total')
                }
            moves = self.env['account.move'].browse([m.id for m in matching_moves])

        # Check payment status if required
        if self.require_payment:
            paid_moves = moves.filtered(lambda m: m.payment_state == 'paid')
            if not paid_moves:
                return False, {
                    'message': f'Invoices found for {self.partner_id.name} but none are fully paid',
                    'move_ids': moves.ids,
                    'unpaid_count': len(moves)
                }
            moves = paid_moves

        # Determine invoice type for message
        type_map = {
            'out_invoice': 'customer invoice(s)',
            'in_invoice': 'vendor bill(s)',
            'out_refund': 'customer credit note(s)',
            'in_refund': 'vendor credit note(s)',
            'all': 'invoice(s)'
        }
        invoice_type = type_map.get(self.move_type, 'invoice(s)')

        return True, {
            'message': f'Partner invoice check passed: {len(moves)} {invoice_type} found for {self.partner_id.name}',
            'move_count': len(moves),
            'total_amount': sum(moves.mapped('amount_total')),
            'move_ids': moves.ids,
            'partner_name': self.partner_id.name
        }
