Installation
============

To install this module:

1. Download the module and place it in your Odoo addons directory
2. Update the module list (Apps → Update Apps List)
3. Search for "Monthly Compliance Checklist"
4. Click Install

Dependencies
------------

**Required:**

* ``account`` - Odoo Accounting module
* ``mail`` - Odoo Mail module

**Optional:**

* ``base_tier_validation`` - From OCA server-ux repository (for advanced approval workflows)
* ``electric_bills`` - For electric bill compliance features
* ``water_usage`` - For water bill compliance features

Python Dependencies
-------------------

This module uses only standard Odoo dependencies. No additional Python packages are required.

Post-Installation
-----------------

After installation:

1. Configure user permissions (Settings → Users → Access Rights)
2. Create compliance templates (Accounting → Compliance → Check Templates)
3. Enable auto-creation on templates that should generate monthly checklists
4. The daily cron job will automatically create checklists for the current month
