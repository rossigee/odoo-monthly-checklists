# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models


class PaymentAttachmentCheck(models.Model):
    """
    Payment Attachment Compliance Check
    Validates that payment records have required attachments
    """
    _name = 'compliance.check.payment.attachment'
    _description = 'Payment Attachment Check'
    _inherit = 'abstract.compliance.check'
    _table = 'compliance_check_payment_attachment'

    # Registration info for the check type registry
    _compliance_check_type = 'payment_attachment'
    _compliance_check_name = 'Payment Attachment Check'

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
        help='Minimum number of required attachments per payment'
    )
    max_attachments = fields.Integer(
        string='Maximum Attachments',
        help='Maximum allowed attachments per payment (0 = unlimited)'
    )
    filename_pattern = fields.Char(
        string='Filename Pattern',
        help='Regex pattern for filename validation (e.g., "receipt.*\\.pdf")'
    )
    min_filesize_kb = fields.Integer(
        string='Minimum File Size (KB)',
        help='Minimum file size in kilobytes'
    )
    max_filesize_kb = fields.Integer(
        string='Maximum File Size (KB)',
        help='Maximum file size in kilobytes'
    )

    # Computed field for human-readable summary
    condition_summary = fields.Text(
        string='Condition Summary',
        compute='_compute_condition_summary',
        help='Human-readable description of this check condition'
    )

    @api.depends('attachment_types', 'min_attachments', 'max_attachments', 'filename_pattern', 'min_filesize_kb', 'max_filesize_kb')
    def _compute_condition_summary(self):
        """Generate human-readable summary of the check condition"""
        for record in self:
            parts = ["Payment records must have"]

            # Attachment count
            if record.max_attachments > 0 and record.min_attachments != record.max_attachments:
                parts.append(f"{record.min_attachments}-{record.max_attachments} attachments")
            elif record.min_attachments > 1:
                parts.append(f"at least {record.min_attachments} attachments")
            else:
                parts.append("at least 1 attachment")

            # File type
            type_map = {
                'pdf': 'PDF documents',
                'image': 'image files',
                'excel': 'Excel/CSV files',
                'any': 'any file type'
            }
            if record.attachment_types in type_map:
                parts.append(f"of type: {type_map[record.attachment_types]}")

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

            record.condition_summary = " ".join(parts) + "."

    @api.model
    def get_evaluation_fields(self):
        """Return fields relevant for payment attachment evaluation"""
        base_fields = super().get_evaluation_fields()
        return base_fields + [
            'attachment_types', 'min_attachments', 'max_attachments',
            'filename_pattern', 'min_filesize_kb', 'max_filesize_kb'
        ]

    @classmethod
    def get_view_ids(cls, env):
        """Return view IDs for this check type"""
        return {
            'form': env.ref('monthly_compliance_checklist.view_payment_attachment_check_form').id,
            'tree': env.ref('monthly_compliance_checklist.view_payment_attachment_check_tree').id,
            'search': env.ref('monthly_compliance_checklist.view_payment_attachment_check_search').id,
            'action': env.ref('monthly_compliance_checklist.action_payment_attachment_check').id,
        }

    @api.model
    def get_configuration_action(self):
        """Return action to open this check type's configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Attachment Check Configuration',
            'res_model': self._name,
            'view_mode': 'form',
            'view_id': self.env.ref('monthly_compliance_checklist.view_payment_attachment_check_form').id,
            'target': 'new',
            'context': {'default_name': 'New Payment Attachment Check'}
        }

    def evaluate_condition(self, year, month):
        """
        Evaluate payment attachment check for the given month/year.
        Returns: (is_met: bool, details: dict)
        """
        start_date, end_date = self._get_month_date_range(year, month)

        # Find payment records (account.payment) for the period
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', '=', 'posted')
        ]

        payments = self.env['account.payment'].search(domain)

        if not payments:
            return False, {'message': 'No payments found for this period'}

        matching_payments = []

        for payment in payments:
            if not payment.attachment_ids:
                continue

            attachments = payment.attachment_ids

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

            matching_payments.append(payment)

        if not matching_payments:
            return False, {'message': 'No payments found meeting attachment requirements'}

        return True, {
            'message': f'Payment attachment check passed: {len(matching_payments)} payment(s) with valid attachments',
            'payment_count': len(matching_payments),
            'payment_ids': [p.id for p in matching_payments]
        }
