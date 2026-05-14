#!/bin/bash
set -e

# Export PostgreSQL environment variables
export PGHOST=postgres
export PGPORT=5432
export PGUSER=odoo
export PGPASSWORD=odoo

# Install required Python dependencies from manifest
pip install requests coverage

# Initialize database
odoo -d test_db --init=base --stop-after-init

# Install module and run tests
odoo -d test_db --init=monthly_compliance_checklist --stop-after-init --test-tags=/monthly_compliance_checklist --log-level=info

# Run tests
# echo "Running tests with module path..."
# odoo -d test_db --test-tags=/monthly_compliance_checklist --stop-after-init

echo "Tests completed successfully!"