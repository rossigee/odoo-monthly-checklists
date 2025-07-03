# -*- coding: utf-8 -*-

from odoo import models, fields, api
import calendar


class ElectricBillCompliance(models.Model):
    """
    Electric Bill Compliance Condition
    
    Validates the complete electric bill payment process:
    1. Electric bill data imported (non-zero units)
    2. Invoice created with attachment (above minimum amount)
    3. Payment processed with attachment
    4. Bank statement reconciles the payment
    5. Invoice marked as reconciled
    6. Summary posted to communication channel
    """
    _name = 'electric.bill.compliance'
    _inherit = 'compliance.condition.abstract'
    _description = 'Electric Bill Compliance Condition'
    
    # Electric bill specific fields
    minimum_amount = fields.Float(
        string='Minimum Expected Amount',
        default=50.0,
        help='Minimum expected invoice amount for validation'
    )
    
    # Relationships to track validation progress
    electric_bill_record_id = fields.Many2one(
        'electric.bill',
        string='Electric Bill Record',
        help='Related electric bill data record'
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        help='Related invoice for electric bill'
    )
    payment_ids = fields.Many2many(
        'account.payment',
        string='Payments',
        help='Payments made for this electric bill'
    )
    
    # Status tracking for each validation step
    step_1_data_imported = fields.Boolean(
        string='Data Imported',
        default=False,
        help='Electric bill data has been imported'
    )
    step_2_invoice_created = fields.Boolean(
        string='Invoice Created',
        default=False,
        help='Invoice has been created with proper attachment'
    )
    step_3_payment_processed = fields.Boolean(
        string='Payment Processed',
        default=False,
        help='Payment has been processed with attachment'
    )
    step_4_bank_reconciled = fields.Boolean(
        string='Bank Reconciled',
        default=False,
        help='Bank statement has been reconciled'
    )
    step_5_invoice_reconciled = fields.Boolean(
        string='Invoice Reconciled',
        default=False,
        help='Invoice has been marked as reconciled'
    )
    step_6_notification_sent = fields.Boolean(
        string='Notification Sent',
        default=False,
        help='Summary has been posted to communication channel'
    )
    
    def _compute_validation_steps(self):
        """Compute the status of each validation step"""
        for condition in self:
            try:
                # Step 1: Check if electric bill data exists
                condition.step_1_data_imported = condition._check_step_1_data_imported()
                
                # Step 2: Check if invoice exists with attachment
                condition.step_2_invoice_created = condition._check_step_2_invoice_created()
                
                # Step 3: Check if payment processed with attachment
                condition.step_3_payment_processed = condition._check_step_3_payment_processed()
                
                # Step 4: Check if bank reconciled
                condition.step_4_bank_reconciled = condition._check_step_4_bank_reconciled()
                
                # Step 5: Check if invoice reconciled
                condition.step_5_invoice_reconciled = condition._check_step_5_invoice_reconciled()
                
                # Step 6: Check if notification sent
                condition.step_6_notification_sent = condition._check_step_6_notification_sent()
            except Exception:
                # Set defaults if computation fails
                condition.step_1_data_imported = False
                condition.step_2_invoice_created = False
                condition.step_3_payment_processed = False
                condition.step_4_bank_reconciled = False
                condition.step_5_invoice_reconciled = False
                condition.step_6_notification_sent = False
    
    def _check_step_1_data_imported(self):
        """Check if electric bill data has been imported for the month"""
        if not self.year or not self.month:
            return False
            
        # Look for electric bill record for this month
        electric_bill = self.env['electric.bill'].search([
            ('year', '=', self.year),
            ('month', '=', self.month),
            ('units', '>', 0)
        ], limit=1)
        
        if electric_bill:
            # Note: Don't assign Many2one fields in computed methods to avoid RPC errors
            # self.electric_bill_record_id = electric_bill.id
            return True
        return False
    
    def _check_step_2_invoice_created(self):
        """Check if invoice exists with proper amount and attachment"""
        if not self.year or not self.month:
            return False
            
        # Date range for the month
        start_date, end_date = self._get_month_date_range()
        
        # Look for posted invoice in the month
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('amount_total', '>=', self.minimum_amount),
            # Add domain for electric company partner if needed
        ])
        
        for invoice in invoices:
            # Check if invoice has attachment
            if invoice.attachment_ids:
                # Note: Don't assign Many2one fields in computed methods to avoid RPC errors
                # self.invoice_id = invoice.id
                return True
        return False
    
    def _check_step_3_payment_processed(self):
        """Check if payment has been processed with attachment"""
        if not self.invoice_id:
            return False
            
        # Get payments for this invoice
        payments = self.invoice_id._get_reconciled_payments()
        
        for payment in payments:
            if payment.attachment_ids:
                # Note: Don't assign Many2many fields in computed methods to avoid RPC errors
                # self.payment_ids = [(6, 0, payments.ids)]
                return True
        return False
    
    def _check_step_4_bank_reconciled(self):
        """Check if bank statement has been reconciled"""
        if not self.payment_ids:
            return False
            
        # Check if any payment is reconciled with bank statement
        for payment in self.payment_ids:
            if payment.is_reconciled:
                return True
        return False
    
    def _check_step_5_invoice_reconciled(self):
        """Check if invoice is fully reconciled"""
        if not self.invoice_id:
            return False
            
        return self.invoice_id.payment_state == 'paid'
    
    def _check_step_6_notification_sent(self):
        """Check if notification has been sent to communication channel"""
        if not self.invoice_id:
            return False
            
        # Look for message posted to specific channel
        # This would depend on your Discord integration or mail channel setup
        # For now, check if there's a message about this invoice
        messages = self.env['mail.message'].search([
            ('res_id', '=', self.invoice_id.id),
            ('model', '=', 'account.move'),
            ('body', 'ilike', 'electric'),
            ('message_type', '=', 'notification')
        ])
        
        return len(messages) > 0
    
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
                condition.condition_state = 'incomplete'
            elif condition.warning_count > 0:
                condition.condition_state = 'warnings'  
            elif all([
                condition.step_1_data_imported,
                condition.step_2_invoice_created,
                condition.step_3_payment_processed,
                condition.step_4_bank_reconciled,
                condition.step_5_invoice_reconciled,
                condition.step_6_notification_sent
            ]):
                condition.condition_state = 'complete'
            else:
                condition.condition_state = 'incomplete'
    
    def _run_validation_checks(self):
        """Run all validation checks and return results"""
        results = []
        
        # Step 1: Data Import Check
        if self.step_1_data_imported:
            results.append({
                'check_name': 'Electric Bill Data Import',
                'status': 'success',
                'message': f'Electric bill data imported for {self.year}/{self.month:02d}',
                'details': f'Record ID: {self.electric_bill_record_id.id}' if self.electric_bill_record_id else ''
            })
        else:
            results.append({
                'check_name': 'Electric Bill Data Import',
                'status': 'error',
                'message': f'No electric bill data found for {self.year}/{self.month:02d}',
                'details': 'Please import electric bill data with non-zero units'
            })
        
        # Step 2: Invoice Check
        if self.step_2_invoice_created:
            results.append({
                'check_name': 'Invoice Creation',
                'status': 'success',
                'message': f'Invoice created: {self.invoice_id.name}',
                'details': f'Amount: {self.invoice_id.amount_total}, Attachments: {len(self.invoice_id.attachment_ids)}'
            })
        else:
            if self.invoice_id and self.invoice_id.amount_total < self.minimum_amount:
                results.append({
                    'check_name': 'Invoice Creation', 
                    'status': 'warning',
                    'message': f'Invoice amount ({self.invoice_id.amount_total}) below minimum ({self.minimum_amount})',
                    'details': 'Invoice exists but amount seems low'
                })
            else:
                results.append({
                    'check_name': 'Invoice Creation',
                    'status': 'error', 
                    'message': 'No valid invoice found for this month',
                    'details': f'Expected posted invoice >= {self.minimum_amount} with attachment'
                })
        
        # Step 3: Payment Check
        if self.step_3_payment_processed:
            results.append({
                'check_name': 'Payment Processing',
                'status': 'success', 
                'message': f'Payment processed with attachment',
                'details': f'Payments: {len(self.payment_ids)}'
            })
        else:
            results.append({
                'check_name': 'Payment Processing',
                'status': 'error',
                'message': 'No payment with attachment found',
                'details': 'Payment must have supporting attachment'
            })
        
        # Step 4: Bank Reconciliation Check
        if self.step_4_bank_reconciled:
            results.append({
                'check_name': 'Bank Reconciliation',
                'status': 'success',
                'message': 'Payment reconciled with bank statement'
            })
        else:
            results.append({
                'check_name': 'Bank Reconciliation', 
                'status': 'error',
                'message': 'Payment not reconciled with bank statement'
            })
        
        # Step 5: Invoice Reconciliation Check
        if self.step_5_invoice_reconciled:
            results.append({
                'check_name': 'Invoice Reconciliation',
                'status': 'success',
                'message': 'Invoice fully paid and reconciled'
            })
        else:
            results.append({
                'check_name': 'Invoice Reconciliation',
                'status': 'error', 
                'message': 'Invoice not fully reconciled'
            })
        
        # Step 6: Notification Check
        if self.step_6_notification_sent:
            results.append({
                'check_name': 'Notification Sent',
                'status': 'success',
                'message': 'Summary posted to communication channel'
            })
        else:
            results.append({
                'check_name': 'Notification Sent',
                'status': 'warning',
                'message': 'No notification found in communication channel',
                'details': 'Consider posting summary to #payments channel'
            })
        
        return results
    
    @api.model
    def create_for_checklist(self, checklist_id, year, month):
        """Factory method to create electric bill compliance condition"""
        return self.create({
            'name': f'Electric Bills - {year}/{month:02d}',
            'description': 'Complete electric bill payment process validation',
            'checklist_id': checklist_id,
            'year': year,
            'month': month,
            'sequence': 10,
        })