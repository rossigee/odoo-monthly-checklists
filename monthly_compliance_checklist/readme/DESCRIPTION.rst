Monthly Compliance Checklist
============================

This module provides automated financial compliance tracking for Odoo. It creates monthly checklists based on configurable templates that track required account transactions and partner activities.

Key Features
------------

* **Automated Monthly Generation**: Daily cron job creates checklists from active templates
* **Real-time Tracking**: Automatic updates when transactions are posted
* **Flexible Validation**: Support for multiple check types and conditions
* **Progress Monitoring**: Visual completion tracking with percentages
* **Historical Backfill**: Create checklists for past months via wizard
* **Audit Trail**: Full activity logging via mail.thread integration

Check Types
-----------

The module supports several types of compliance checks:

* **Partner Payment Checks**: Validate payments to/from specific partners
* **Partner Invoice Checks**: Ensure invoices exist for partners
* **Attachment Checks**: Verify documents are attached to transactions
* **Payment with Attachment**: Combined payment and document validation
* **Invoice with Attachment**: Combined invoice and document validation

Advanced Features
-----------------

* **Hierarchical Validation**: Support for complex business processes
* **Three-state System**: incomplete → warnings → complete
* **Extensible Framework**: Easy to add new compliance types
* **Tier Validation Ready**: Integration with OCA base_tier_validation (optional)