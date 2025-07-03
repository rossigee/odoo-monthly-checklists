# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re


class InvoiceAttachmentCheck(models.Model):
    """
    Invoice Attachment Compliance Check
    Validates that invoice/bill records have required attachments
    """
    _name = 'compliance.check.invoice.attachment'
    _description = 'Invoice Attachment Check'
    _inherit = 'abstract.compliance.check'
    _table = 'compliance_check_invoice_attachment'
    
    # Registration info for the check type registry
    _compliance_check_type = 'invoice_attachment'
    _compliance_check_name = 'Invoice Attachment Check'
    
    # Invoice type filter
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoices'),
        ('in_invoice', 'Vendor Bills'),
        ('out_refund', 'Customer Credit Notes'),
        ('in_refund', 'Vendor Credit Notes'),
        ('all', 'All Invoice Types')
    ], string='Invoice Type', default='in_invoice')
    
    # Attachment requirement fields
    attachment_types = fields.Selection([
        ('pdf', 'PDF Documents'),
        ('image', 'Images (PNG, JPG)'),
        ('excel', 'Excel/CSV Files'),
        ('any', 'Any File Type')
    ], string='Required File Types', default='pdf')
    
    min_attachments = fields.Integer(
        string='Minimum Attachments',
        default=1,
        help='Minimum number of required attachments per invoice'
    )
    max_attachments = fields.Integer(
        string='Maximum Attachments',
        help='Maximum allowed attachments per invoice (0 = unlimited)'
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
    
    # Partner filter
    partner_ids = fields.Many2many(
        'res.partner',
        string='Specific Partners',
        help='Only check invoices from these partners (leave empty for all partners)'
    )
    
    # Computed field for human-readable summary
    condition_summary = fields.Text(
        string='Condition Summary',
        compute='_compute_condition_summary',
        help='Human-readable description of this check condition'
    )
    
    @api.depends('move_type', 'attachment_types', 'min_attachments', 'max_attachments', 'filename_pattern', 'min_filesize_kb', 'max_filesize_kb', 'partner_ids')
    def _compute_condition_summary(self):
        """Generate human-readable summary of the check condition"""
        for record in self:
            # Invoice type
            type_map = {
                'out_invoice': 'Customer invoices',
                'in_invoice': 'Vendor bills',
                'out_refund': 'Customer credit notes',
                'in_refund': 'Vendor credit notes',
                'all': 'All invoices/bills'
            }
            invoice_type = type_map.get(record.move_type, 'Invoice records')
            
            parts = [f"{invoice_type} must have"]
            
            # Attachment count
            if record.max_attachments > 0 and record.min_attachments != record.max_attachments:
                parts.append(f"{record.min_attachments}-{record.max_attachments} attachments")
            elif record.min_attachments > 1:
                parts.append(f"at least {record.min_attachments} attachments")
            else:
                parts.append("at least 1 attachment")
            
            # File type
            file_type_map = {
                'pdf': 'PDF documents',
                'image': 'image files',
                'excel': 'Excel/CSV files',
                'any': 'any file type'
            }
            if record.attachment_types in file_type_map:
                parts.append(f"of type: {file_type_map[record.attachment_types]}")
            
            # Additional constraints
            constraints = []
            if record.filename_pattern:
                constraints.append(f"filename matching '{record.filename_pattern}'")
            if record.min_filesize_kb:
                constraints.append(f"size ≥ {record.min_filesize_kb}KB")
            if record.max_filesize_kb:
                constraints.append(f"size ≤ {record.max_filesize_kb}KB")
            
            if constraints:
                parts.append(f"with {'; '.join(constraints)}")
            
            # Partner filter
            if record.partner_ids:
                if len(record.partner_ids) == 1:
                    parts.append(f"from partner '{record.partner_ids[0].name}'")
                else:
                    parts.append(f"from {len(record.partner_ids)} specific partners")
            
            record.condition_summary = " ".join(parts) + "."
    
    @api.model
    def get_evaluation_fields(self):
        """Return fields relevant for invoice attachment evaluation"""
        base_fields = super().get_evaluation_fields()
        return base_fields + [
            'move_type', 'attachment_types', 'min_attachments', 'max_attachments', 
            'filename_pattern', 'min_filesize_kb', 'max_filesize_kb', 'partner_ids'
        ]
    
    @classmethod
    def get_view_ids(cls, env):
        """Return view IDs for this check type"""
        return {
            'form': env.ref('monthly_compliance_checklist.view_invoice_attachment_check_form').id,
            'tree': env.ref('monthly_compliance_checklist.view_invoice_attachment_check_tree').id,
            'search': env.ref('monthly_compliance_checklist.view_invoice_attachment_check_search').id,
            'action': env.ref('monthly_compliance_checklist.action_invoice_attachment_check').id,
        }
    
    @api.model
    def get_configuration_action(self):
        """Return action to open this check type's configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Attachment Check Configuration',
            'res_model': self._name,
            'view_mode': 'form',
            'view_id': self.env.ref('monthly_compliance_checklist.view_invoice_attachment_check_form').id,
            'target': 'new',
            'context': {'default_name': 'New Invoice Attachment Check'}
        }
    
    def evaluate_condition(self, year, month):
        """
        Evaluate invoice attachment check for the given month/year.
        Returns: (is_met: bool, details: dict)
        """
        start_date, end_date = self._get_month_date_range(year, month)
        
        # Build domain for invoice/bill records
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', '=', 'posted')
        ]
        
        # Filter by move type
        if self.move_type != 'all':
            domain.append(('move_type', '=', self.move_type))
        else:
            domain.append(('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']))
        
        # Filter by specific partners if configured
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        moves = self.env['account.move'].search(domain)
        
        if not moves:
            return False, {'message': 'No invoices found for this period'}
        
        matching_moves = []
        
        for move in moves:
            if not move.attachment_ids:
                continue
            
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
            
            # Check attachment count
            if len(attachments) < self.min_attachments:
                continue
            if self.max_attachments > 0 and len(attachments) > self.max_attachments:
                continue
            
            # Check filename pattern if specified
            if self.filename_pattern:
                pattern_matches = any(
                    re.search(self.filename_pattern, attachment.name or '')
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
            return False, {'message': 'No invoices found meeting attachment requirements'}
        
        return True, {
            'message': f'Invoice attachment check passed: {len(matching_moves)} invoice(s) with valid attachments',
            'move_count': len(matching_moves),
            'move_ids': [m.id for m in matching_moves]
        }