# © 2025
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestMonthlyChecklist(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test data
        cls.template1 = cls.env["check.template"].create(
            {
                "name": "Test Template 1",
                "sequence": 10,
                "auto_create_monthly": True,
                "check_type": "attachment_check",
            }
        )

        cls.template2 = cls.env["check.template"].create(
            {
                "name": "Test Template 2",
                "sequence": 20,
                "auto_create_monthly": True,
                "check_type": "partner_payment_check",
            }
        )

    def test_create_monthly_checklist(self):
        """Test creation of monthly checklist"""
        checklist = self.env["monthly.checklist"].create(
            {
                "period_date": date(2025, 1, 1),
            }
        )

        self.assertEqual(checklist.state, "draft")
        self.assertEqual(checklist.period_display, "2025-01")
        self.assertEqual(checklist.year, 2025)
        self.assertEqual(checklist.month, 1)
        self.assertEqual(checklist.name, "Compliance Checklist - 2025-01")

    def test_generate_check_instances(self):
        """Test automatic generation of check instances"""
        checklist = self.env["monthly.checklist"].create(
            {
                "period_date": date(2025, 1, 1),
            }
        )

        # Generate instances from templates
        checklist.generate_check_instances()

        self.assertEqual(len(checklist.check_instance_ids), 2)
        self.assertEqual(checklist.total_items, 2)
        self.assertEqual(checklist.completed_items, 0)
        self.assertEqual(checklist.completion_percentage, 0.0)

    def test_checklist_state_transitions(self):
        """Test state transitions"""
        checklist = self.env["monthly.checklist"].create(
            {
                "period_date": date(2025, 1, 1),
            }
        )

        # Draft to active
        checklist.action_activate()
        self.assertEqual(checklist.state, "active")

        # Cannot complete without 100% completion
        with self.assertRaises(ValidationError):
            checklist.action_complete()

        # Cancel
        checklist.action_cancel()
        self.assertEqual(checklist.state, "cancelled")

        # Reset to draft
        checklist.action_reset_draft()
        self.assertEqual(checklist.state, "draft")

    def test_completion_percentage_calculation(self):
        """Test completion percentage updates"""
        checklist = self.env["monthly.checklist"].create(
            {
                "period_date": date(2025, 1, 1),
            }
        )
        checklist.generate_check_instances()
        checklist.action_activate()

        # Mark one instance as complete
        instance = checklist.check_instance_ids[0]
        instance.is_completed = True

        # Force recomputation
        checklist._compute_completion_stats()

        self.assertEqual(checklist.completed_items, 1)
        self.assertEqual(checklist.completion_percentage, 50.0)

        # Mark all complete
        checklist.check_instance_ids.write({"is_completed": True})
        checklist._compute_completion_stats()

        self.assertEqual(checklist.completed_items, 2)
        self.assertEqual(checklist.completion_percentage, 100.0)

    def test_create_current_month_checklist(self):
        """Test cron job functionality"""
        # Test current month creation
        model = self.env["monthly.checklist"]
        model.create_current_month_checklist()

        current_month = date.today().replace(day=1)
        checklist = model.search([("period_date", "=", current_month)])

        self.assertTrue(checklist)
        self.assertEqual(checklist.period_date, current_month)

        # Running again should not create duplicate
        count_before = model.search_count([])
        model.create_current_month_checklist()
        count_after = model.search_count([])

        self.assertEqual(count_before, count_after)

    def test_period_uniqueness(self):
        """Test that only one checklist per period is allowed"""
        self.env["monthly.checklist"].create(
            {
                "period_date": date(2025, 2, 1),
            }
        )

        with self.assertRaises(ValidationError):
            self.env["monthly.checklist"].create(
                {
                    "period_date": date(2025, 2, 15),  # Same month
                }
            )
