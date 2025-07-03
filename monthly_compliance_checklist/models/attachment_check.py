# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re


class AttachmentCheck(models.Model):
    """
    Attachment Compliance Check
    Validates that transactions have required attachments with specific criteria
    """
    _name = 'compliance.check.attachment'
    _description = 'Attachment Requirements Check'
    _inherit = 'abstract.compliance.check'
    _table = 'compliance_check_attachment'
    
    # Registration info for the check type registry
    _compliance_check_type = 'attachment_check'
    _compliance_check_name = 'Attachment Requirements'
    
    # Attachment specific fields
    attachment_types = fields.Selection([
        ('pdf', 'PDF Documents'),
        ('image', 'Images (PNG, JPG)'),
        ('excel', 'Excel/CSV Files'),
        ('any', 'Any File Type')
    ], string='Required File Types', default='pdf')
    
    min_attachments = fields.Integer(
        string='Minimum Attachments',
        default=1,
        help='Minimum number of required attachments'
    )
    max_attachments = fields.Integer(
        string='Maximum Attachments',
        help='Maximum allowed attachments (0 = unlimited)'
    )
    filename_pattern = fields.Char(
        string='Filename Pattern',
        help='Regex pattern for filename validation (e.g., "invoice.*\\.pdf")'
    )
    min_filesize_kb = fields.Integer(
        string='Minimum File Size (KB)',
        help='Minimum file size in kilobytes'
    )
    max_filesize_kb = fields.Integer(
        string='Maximum File Size (KB)',
        help='Maximum file size in kilobytes'
    )
    require_all_transactions = fields.Boolean(
        string='All Transactions Must Have Attachments',
        default=False,
        help='If checked, ALL transactions in the period must meet attachment requirements'
    )
    partner_filter = fields.Many2one(
        'res.partner',
        string='Filter by Partner',
        help='Only check transactions from this partner'
    )
    account_filter = fields.Many2many(
        'account.account',
        string='Filter by Accounts',
        help='Only check transactions affecting these accounts'
    )
    
    @api.model
    def get_evaluation_fields(self):
        """Return fields relevant for attachment evaluation"""
        base_fields = super().get_evaluation_fields()
        return base_fields + [
            'attachment_types', 'min_attachments', 'max_attachments',
            'filename_pattern', 'min_filesize_kb', 'max_filesize_kb',
            'require_all_transactions', 'partner_filter', 'account_filter'
        ]
    
    @classmethod
    def get_view_ids(cls, env):
        """Return view IDs for this check type"""
        return {
            'form': env.ref('monthly_compliance_checklist.view_attachment_check_form').id,
            'tree': env.ref('monthly_compliance_checklist.view_attachment_check_tree').id,
            'search': env.ref('monthly_compliance_checklist.view_attachment_check_search').id,
            'action': env.ref('monthly_compliance_checklist.action_attachment_check').id,
        }
    
    @api.model
    def get_configuration_action(self):
        """Return action to open this check type's configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attachment Check Configuration',
            'res_model': self._name,
            'view_mode': 'form',
            'view_id': self.env.ref('monthly_compliance_checklist.view_attachment_check_form').id,
            'target': 'new',
            'context': {'default_name': 'New Attachment Check'}
        }
    
    def evaluate_condition(self, year, month):
        """
        Evaluate attachment requirements for the given month/year.
        Returns: (is_met: bool, details: dict)
        """
        start_date, end_date = self._get_month_date_range(year, month)
        
        # Build domain for transactions to check
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', '=', 'posted')
        ]
        
        # Add optional filters
        if self.partner_filter:
            domain.append(('partner_id', '=', self.partner_filter.id))
        if self.account_filter:
            domain.append(('line_ids.account_id', 'in', self.account_filter.ids))
        
        moves = self.env['account.move'].search(domain)
        
        if not moves:
            return False, {'message': 'No transactions found for this period'}
        
        matching_moves = []
        failed_moves = []
        
        for move in moves:
            meets_requirements, failure_reason = self._check_move_attachments(move)
            
            if meets_requirements:
                matching_moves.append(move)
            else:
                failed_moves.append((move, failure_reason))
        
        # Determine if check passes
        if self.require_all_transactions:
            # All transactions must meet requirements
            is_met = len(failed_moves) == 0
            if not is_met:
                return False, {
                    'message': f'{len(failed_moves)} of {len(moves)} transactions failed attachment requirements',
                    'failed_count': len(failed_moves),
                    'total_count': len(moves),
                    'failed_move_ids': [move.id for move, reason in failed_moves],
                    'failure_reasons': [reason for move, reason in failed_moves]
                }
        else:
            # At least one transaction must meet requirements
            is_met = len(matching_moves) > 0
            if not is_met:
                return False, {
                    'message': 'No transactions found meeting attachment requirements',
                    'total_count': len(moves),
                    'failed_move_ids': [move.id for move, reason in failed_moves]
                }
        
        return True, {
            'message': f'Attachment check passed: {len(matching_moves)} of {len(moves)} transaction(s) meet requirements',
            'matching_count': len(matching_moves),
            'total_count': len(moves),
            'move_ids': [m.id for m in matching_moves]
        }
    
    def _check_move_attachments(self, move):
        """
        Check if a single move meets attachment requirements.
        Returns: (meets_requirements: bool, failure_reason: str)
        """
        if not move.attachment_ids:
            return False, 'No attachments found'
        
        attachments = move.attachment_ids
        
        # Filter by file type if specified
        if self.attachment_types != 'any':
            if self.attachment_types == 'pdf':
                attachments = attachments.filtered(lambda a: a.mimetype == 'application/pdf')
            elif self.attachment_types == 'image':
                attachments = attachments.filtered(lambda a: a.mimetype.startswith('image/'))
            elif self.attachment_types == 'excel':
                attachments = attachments.filtered(lambda a: a.mimetype in [
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'text/csv'
                ])
        
        if not attachments:
            return False, f'No {self.attachment_types} attachments found'
        
        # Check attachment count
        if len(attachments) < self.min_attachments:
            return False, f'Only {len(attachments)} attachments found, need at least {self.min_attachments}'
        
        if self.max_attachments > 0 and len(attachments) > self.max_attachments:
            return False, f'Too many attachments: {len(attachments)}, maximum allowed: {self.max_attachments}'
        
        # Check filename pattern if specified
        if self.filename_pattern:
            pattern_matches = any(
                re.search(self.filename_pattern, attachment.name or '')
                for attachment in attachments
            )
            if not pattern_matches:
                return False, f'No attachments match filename pattern: {self.filename_pattern}'
        
        # Check file sizes if specified
        if self.min_filesize_kb or self.max_filesize_kb:
            for attachment in attachments:
                size_kb = (attachment.file_size or 0) / 1024
                if self.min_filesize_kb and size_kb < self.min_filesize_kb:
                    return False, f'Attachment {attachment.name} too small: {size_kb:.1f}KB < {self.min_filesize_kb}KB'
                if self.max_filesize_kb and size_kb > self.max_filesize_kb:
                    return False, f'Attachment {attachment.name} too large: {size_kb:.1f}KB > {self.max_filesize_kb}KB'
        
        return True, 'All attachment requirements met'