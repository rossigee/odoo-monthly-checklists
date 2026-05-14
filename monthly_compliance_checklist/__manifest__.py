# Copyright 2025 Ross Golder (https://golder.org)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Monthly Compliance Checklist",
    "version": "16.0.1.0.1",
    "author": "Ross Golder",
    "website": "https://golder.org/",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Track monthly financial compliance requirements with automated checklist management.",
    "depends": [
        "account",
        "mail",
        # 'base_tier_validation',  # Temporarily disabled
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/compliance_cron.xml",
        "data/partner_payment_check_views.xml",
        "data/partner_invoice_check_views.xml",
        "data/payment_attachment_check_views.xml",
        "data/invoice_attachment_check_views.xml",
        "data/attachment_check_views.xml",
        "data/electric_bill_templates.xml",
        "views/check_template_views.xml",
        "views/check_instance_views.xml",
        "views/monthly_checklist_views.xml",
        "views/compliance_backfill_wizard_views.xml",
        "views/electric_bill_compliance_views.xml",
        "views/water_bill_compliance_views.xml",
        "views/compliance_menu.xml",
    ],
    "installable": True,
    "auto_install": False,
}
