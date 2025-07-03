# © 2025
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, datetime
from odoo.tests import TransactionCase


class TestCheckInstance(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'is_company': True,
        })
        
        # Create test accounts
        cls.account_receivable = cls.env['account.account'].create({
            'name': 'Test Receivable',
            'code': 'TEST_REC',
            'account_type': 'asset_receivable',
        })
        
        cls.account_expense = cls.env['account.account'].create({
            'name': 'Test Expense',
            'code': 'TEST_EXP',
            'account_type': 'expense',
        })
        
        # Create journal
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Journal',
            'code': 'TEST',
            'type': 'general',
        })
        
        # Create template and checklist
        cls.template = cls.env['check.template'].create({
            'name': 'Test Partner Payment',
            'check_type': 'partner_payment_check',
            'partner_ids': [(6, 0, [cls.partner.id])],
            'minimum_amount': 100.0,
        })
        
        cls.checklist = cls.env['monthly.checklist'].create({
            'period_date': date(2025, 1, 1),
        })
        
    def test_check_instance_creation(self):
        """Test check instance creation"""
        instance = self.env['check.instance'].create({
            'name': 'Test Instance',
            'template_id': self.template.id,
            'checklist_id': self.checklist.id,
        })
        
        self.assertEqual(instance.year, 2025)
        self.assertEqual(instance.month, 1)
        self.assertFalse(instance.is_completed)
        self.assertFalse(instance.completion_date)
        
    def test_partner_payment_validation(self):
        """Test partner payment check validation"""
        # Create check instance
        instance = self.env['check.instance'].create({
            'name': 'Partner Payment Check',
            'template_id': self.template.id,
            'checklist_id': self.checklist.id,
        })
        
        # Initially not completed
        self.assertFalse(instance.is_completed)
        
        # Create a payment move
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': date(2025, 1, 15),
            'journal_id': self.journal.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_expense.id,
                    'partner_id': self.partner.id,
                    'debit': 150.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.account_receivable.id,
                    'partner_id': self.partner.id,
                    'debit': 0.0,
                    'credit': 150.0,
                }),
            ],
        })
        
        # Post the move
        move.action_post()
        
        # Re-evaluate the instance
        instance._compute_is_completed()
        
        # Should be completed now (amount > minimum)
        self.assertTrue(instance.is_completed)
        
    def test_attachment_check_validation(self):
        """Test attachment check validation"""
        # Create attachment template
        attachment_template = self.env['check.template'].create({
            'name': 'Test Attachment Check',
            'check_type': 'attachment_check',
            'file_types': 'pdf',
        })
        
        # Create instance
        instance = self.env['check.instance'].create({
            'name': 'Attachment Check Instance',
            'template_id': attachment_template.id,
            'checklist_id': self.checklist.id,
        })
        
        # Create a move
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': date(2025, 1, 10),
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Line',
                'account_id': self.account_expense.id,
                'price_unit': 100.0,
            })],
        })
        move.action_post()
        
        # Initially not completed (no attachment)
        instance._compute_is_completed()
        self.assertFalse(instance.is_completed)
        
        # Add attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'test_invoice.pdf',
            'type': 'binary',
            'datas': 'VGVzdCBQREYgY29udGVudA==',  # Base64 "Test PDF content"
            'res_model': 'account.move',
            'res_id': move.id,
        })
        
        # Re-evaluate
        instance._compute_is_completed()
        self.assertTrue(instance.is_completed)
        
    def test_manual_completion(self):
        """Test manual check completion"""
        manual_template = self.env['check.template'].create({
            'name': 'Manual Check',
            'check_type': 'attachment_check',  # Using existing type
        })
        
        instance = self.env['check.instance'].create({
            'name': 'Manual Instance',
            'template_id': manual_template.id,
            'checklist_id': self.checklist.id,
        })
        
        # Manually mark as complete
        instance.is_completed = True
        
        # Should have completion date
        self.assertTrue(instance.completion_date)
        self.assertEqual(instance.completion_date.date(), date.today())