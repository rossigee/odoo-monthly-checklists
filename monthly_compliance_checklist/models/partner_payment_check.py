# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PartnerPaymentCheck(models.Model):
    """
    Partner Payment Compliance Check
    Validates that specific partners have made expected payments
    """
    _name = 'compliance.check.partner.payment'
    _description = 'Partner Payment Check'
    _inherit = 'abstract.compliance.check'
    _table = 'compliance_check_partner_payment'
    
    # Registration info for the check type registry
    _compliance_check_type = 'partner_payment'
    _compliance_check_name = 'Partner Payment Check'
    
    # Partner payment specific fields
    partner_id = fields.Many2one(
        'res.partner',
        string='Required Partner',
        required=True,
        help='Specific partner that must have transactions'
    )
    check_type = fields.Selection([
        ('individual', 'At least one transaction >= minimum'),
        ('sum', 'Total sum >= minimum')
    ], string='Check Type', default='individual', required=True)
    minimum_amount = fields.Float(
        string='Minimum Amount',
        help='Minimum payment amount required (leave 0 for no minimum)'
    )
    maximum_amount = fields.Float(
        string='Maximum Amount',
        help='Maximum payment amount allowed (leave 0 for no maximum)'
    )
    require_reconciliation = fields.Boolean(
        string='Must be Reconciled',
        help='Payment must be reconciled/paid'
    )
    
    # Computed field for human-readable summary
    condition_summary = fields.Text(
        string='Condition Summary',
        compute='_compute_condition_summary',
        help='Human-readable description of this check condition'
    )
    
    @api.depends('partner_id', 'check_type', 'minimum_amount', 'maximum_amount', 'require_reconciliation')
    def _compute_condition_summary(self):
        """Generate human-readable summary of the check condition"""
        for record in self:
            if not record.partner_id:
                record.condition_summary = "No partner specified"
                continue
            
            if record.check_type == 'sum':
                parts = [f"Partner '{record.partner_id.name}' must have total payments"]
            else:
                parts = [f"Partner '{record.partner_id.name}' must have at least one payment"]
            
            # Add amount conditions
            amount_conditions = []
            if record.minimum_amount > 0:
                amount_conditions.append(f"≥ {record.minimum_amount}")
            if record.maximum_amount > 0:
                amount_conditions.append(f"≤ {record.maximum_amount}")
            
            if amount_conditions:
                parts.append(f"with {'total ' if record.check_type == 'sum' else ''}amount {' and '.join(amount_conditions)}")
            
            # Add reconciliation requirement
            if record.require_reconciliation:
                parts.append("that is fully reconciled (paid)")
            
            record.condition_summary = " ".join(parts) + "."
    
    @api.model
    def get_evaluation_fields(self):
        """Return fields relevant for partner payment evaluation"""
        base_fields = super().get_evaluation_fields()
        return base_fields + [
            'partner_id', 'check_type', 'minimum_amount', 'maximum_amount', 'require_reconciliation'
        ]
    
    @classmethod
    def get_view_ids(cls, env):
        """Return view IDs for this check type"""
        return {
            'form': env.ref('monthly_compliance_checklist.view_partner_payment_check_form').id,
            'tree': env.ref('monthly_compliance_checklist.view_partner_payment_check_tree').id,
            'search': env.ref('monthly_compliance_checklist.view_partner_payment_check_search').id,
            'action': env.ref('monthly_compliance_checklist.action_partner_payment_check').id,
        }
    
    @api.model
    def get_configuration_action(self):
        """Return action to open this check type's configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partner Payment Check Configuration',
            'res_model': self._name,
            'view_mode': 'form',
            'view_id': self.env.ref('monthly_compliance_checklist.view_partner_payment_check_form').id,
            'target': 'new',
            'context': {'default_name': 'New Partner Payment Check'}
        }
    
    def evaluate_condition(self, year, month):
        """
        Evaluate partner payment check for the given month/year.
        Returns: (is_met: bool, details: dict)
        """
        start_date, end_date = self._get_month_date_range(year, month)
        
        if not self.partner_id:
            return False, {'message': 'No partner specified for payment check'}
        
        # Find transactions with the required partner
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', '=', 'posted'),
            ('partner_id', '=', self.partner_id.id)
        ]
        
        moves = self.env['account.move'].search(domain)
        
        if not moves:
            return False, {'message': f'No transactions found for partner {self.partner_id.name}'}
        
        # Check reconciliation if required
        if self.require_reconciliation:
            reconciled_moves = moves.filtered(lambda m: m.payment_state == 'paid')
            if not reconciled_moves:
                return False, {
                    'message': f'Transactions found for {self.partner_id.name} but none are reconciled',
                    'move_ids': moves.ids,
                    'unreconciled_count': len(moves)
                }
            moves = reconciled_moves
        
        # Calculate total amount
        total_amount = sum(abs(m.amount_total) for m in moves)
        
        # Check amount conditions
        if self.check_type == 'sum':
            # Check total sum
            if self.minimum_amount > 0 and total_amount < self.minimum_amount:
                return False, {
                    'message': f'Total payments {total_amount} < required minimum {self.minimum_amount} for {self.partner_id.name}',
                    'move_ids': moves.ids,
                    'total_amount': total_amount
                }
            if self.maximum_amount > 0 and total_amount > self.maximum_amount:
                return False, {
                    'message': f'Total payments {total_amount} > allowed maximum {self.maximum_amount} for {self.partner_id.name}',
                    'move_ids': moves.ids,
                    'total_amount': total_amount
                }
        else:
            # Check individual transactions
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
                        'message': f'No transactions found for {self.partner_id.name} with amount {amount_text}',
                        'move_ids': moves.ids,
                        'found_amounts': moves.mapped('amount_total')
                    }
                moves = self.env['account.move'].browse([m.id for m in matching_moves])
                total_amount = sum(abs(m.amount_total) for m in moves)
        
        return True, {
            'message': f'Partner payment check passed: {len(moves)} transaction(s) totaling {total_amount} for {self.partner_id.name}',
            'move_count': len(moves),
            'total_amount': total_amount,
            'move_ids': moves.ids,
            'partner_name': self.partner_id.name
        }