Configuration
=============

Initial Setup
-------------

1. **User Permissions**
   
   Assign users to the appropriate groups:
   
   * **Accounting / Billing**: Read and write access to checklists
   * **Accounting / Billing Administrator**: Full access including deletion

2. **Create Check Templates**
   
   Navigate to **Accounting → Compliance → Check Templates** and create templates for your compliance requirements:
   
   * Set a descriptive name and sequence
   * Choose the check type (partner payment, invoice, attachment, etc.)
   * Configure type-specific settings (partners, accounts, amounts, etc.)
   * Set validity periods if the check only applies for certain dates
   * Enable "Auto Create Monthly" for automatic checklist generation

3. **Configure Cron Job**
   
   The module includes a daily cron job that creates monthly checklists. To adjust:
   
   * Go to **Settings → Technical → Automation → Scheduled Actions**
   * Find "Create Monthly Compliance Checklists"
   * Adjust the execution time or frequency as needed

Template Configuration Examples
-------------------------------

**Partner Payment Check:**

* Name: "Electricity Payment"
* Check Type: Partner Payment Check
* Partners: Your electricity provider
* Minimum Amount: 50.00
* Require Reconciliation: Yes

**Attachment Check:**

* Name: "Invoice Documentation"
* Check Type: Attachment Check
* File Types: pdf
* Filename Pattern: .*invoice.*
* Max File Size: 5 MB

Advanced Configuration
----------------------

**Tier Validation Setup** (requires base_tier_validation):

1. Install the OCA base_tier_validation module
2. Configure tier definitions for compliance conditions
3. Set up approval workflows based on amount thresholds or validation states

**Email Notifications:**

Configure mail templates for compliance reminders:

1. Go to **Settings → Technical → Email → Templates**
2. Create templates for checklist notifications
3. Configure automated actions to send reminders