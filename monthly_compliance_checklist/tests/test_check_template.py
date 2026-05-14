# © 2025
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import TransactionCase


class TestCheckTemplate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test accounts
        cls.account_receivable = cls.env['account.account'].create({
            'name': 'Test Receivable',
            'code': 'TEST001',
            'account_type': 'asset_receivable',
        })

        cls.account_payable = cls.env['account.account'].create({
            'name': 'Test Payable',
            'code': 'TEST002',
            'account_type': 'liability_payable',
        })

        # Create test partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'is_company': True,
        })

    def test_create_check_template(self):
        """Test creation of check template"""
        template = self.env['check.template'].create({
            'name': 'Test Template',
            'sequence': 10,
            'auto_create_monthly': True,
        })

        self.assertTrue(template.active)
        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(template.sequence, 10)

    def test_check_template_with_validity_period(self):
        """Test template with validity dates"""
        template = self.env['check.template'].create({
            'name': 'Limited Template',
            'valid_from': date(2025, 1, 1),
            'valid_until': date(2025, 12, 31),
        })

        self.assertEqual(template.valid_from, date(2025, 1, 1))
        self.assertEqual(template.valid_until, date(2025, 12, 31))

    def test_check_template_types(self):
        """Test different check template types"""
        # Partner payment check
        partner_template = self.env['check.template'].create({
            'name': 'Partner Payment Check',
            'check_type': 'partner_payment_check',
            'partner_ids': [(6, 0, [self.partner.id])],
            'minimum_amount': 100.0,
        })

        self.assertEqual(partner_template.check_type, 'partner_payment_check')
        self.assertEqual(len(partner_template.partner_ids), 1)
        self.assertEqual(partner_template.minimum_amount, 100.0)

        # Partner invoice check
        invoice_template = self.env['check.template'].create({
            'name': 'Partner Invoice Check',
            'check_type': 'partner_invoice_check',
            'partner_ids': [(6, 0, [self.partner.id])],
            'invoice_type': 'out_invoice',
        })

        self.assertEqual(invoice_template.check_type, 'partner_invoice_check')
        self.assertEqual(invoice_template.invoice_type, 'out_invoice')

    def test_attachment_check_template(self):
        """Test attachment check template"""
        template = self.env['check.template'].create({
            'name': 'Attachment Check',
            'check_type': 'attachment_check',
            'file_types': 'pdf',
            'filename_pattern': '.*invoice.*',
            'max_file_size': 5,
        })

        self.assertEqual(template.check_type, 'attachment_check')
        self.assertEqual(template.file_types, 'pdf')
        self.assertEqual(template.filename_pattern, '.*invoice.*')
        self.assertEqual(template.max_file_size, 5)
