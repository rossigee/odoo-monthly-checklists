# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [16.0.1.0.0] - 2025-01-03

### Added
- Initial release of Monthly Compliance Checklist for Odoo 16
- Automated monthly checklist generation from configurable templates
- Real-time compliance tracking based on account transactions
- Check templates with validity periods and multiple validation types
- Account-based, partner-based, and manual check items
- Automatic evaluation of compliance conditions
- Progress tracking with completion percentages
- Backfill wizard for historical checklist creation
- Daily cron job for automatic checklist generation
- Mail thread integration for audit trails
- Comprehensive security model with access controls

### Features
- Abstract compliance framework for extensibility
- Support for complex business process validation
- Three-state validation system (incomplete/warnings/complete)
- Electric bill compliance workflow implementation
- Water bill compliance with usage variance analysis
- Integration with OCA base_tier_validation (optional)

### Technical
- Models: check.template, monthly.checklist, check.instance
- Abstract base: abstract.compliance.check, compliance.condition.abstract
- Specialized compliance types via inheritance pattern
- Computed fields for real-time status updates
- Domain filters for account and partner selection

### Dependencies
- Odoo 16.0 or later
- account module (Odoo Accounting)
- mail module (Odoo Mail)
- base_tier_validation (OCA - optional)