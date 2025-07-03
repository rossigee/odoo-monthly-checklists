# Monthly Compliance Checklist for Odoo

An automated financial compliance tracking module for Odoo 16+ that creates monthly checklists based on configurable templates. Track required account transactions, partner activities, and business processes with automatic validation and progress monitoring.

## 🎯 Key Features

- **Automated Monthly Checklists**: Daily cron job creates checklists from active templates
- **Real-time Compliance Tracking**: Automatic updates when transactions are posted
- **Flexible Validation Rules**: Account-based, partner-based, or manual check items
- **Historical Backfill**: Create checklists for past months via wizard
- **Progress Monitoring**: Visual completion tracking with percentage indicators
- **Audit Trail**: Full activity logging via mail.thread integration

## 🚀 Quick Start

### 1. Install the Module

Place the `monthly_compliance_checklist` folder in your Odoo addons directory and install through the Apps menu.

### 2. Create Compliance Templates

Navigate to **Accounting → Compliance → Check Templates** and create templates for your compliance requirements.

### 3. Enable Auto-creation

Mark templates with `auto_create_monthly` to have them automatically generate monthly checklists.

### 4. Monitor Compliance

Access **Accounting → Compliance → Monthly Checklists** to view and manage compliance status.

## 📋 Requirements

- **Odoo**: 16.0 or later
- **Dependencies**: 
  - `account` (Odoo Accounting)
  - `mail` (Odoo Mail)
  - `base_tier_validation` (OCA - optional for advanced workflows)

## 🏗️ Architecture

The module implements a flexible compliance framework:

- **Check Templates**: Define reusable compliance requirements
- **Monthly Checklists**: Period-specific instances with completion tracking
- **Check Instances**: Individual validation items that auto-evaluate
- **Abstract Compliance**: Extensible framework for complex business processes

## 📖 Advanced Features

### Hierarchical Business Process Validation

The module supports complex compliance workflows like:

- **Electric Bill Compliance**: Data import → Invoice → Payment → Reconciliation
- **Water Bill Compliance**: Usage analysis → Invoice → Payment → Reconciliation
- **Extensible Framework**: Easy to add new compliance types

### Validation States

- `incomplete`: Blocking issues preventing completion
- `warnings`: Non-blocking issues (can proceed with caution)
- `complete`: Fully validated and ready

## 🧪 Testing

Run tests with Odoo's testing framework:

```bash
odoo-bin -d test_db --test-enable --stop-after-init -u monthly_compliance_checklist
```

## 📄 License

This module is licensed under AGPL-3.0.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📞 Support

- **Issues**: Report bugs and feature requests on [GitHub](https://github.com/rossigee/odoo-monthly-checklists/issues)
- **Documentation**: See `monthly_compliance_checklist/readme/` for detailed guides

---

**📊 Note**: This module is designed for financial compliance tracking. Ensure your Odoo accounting data is properly maintained for accurate compliance monitoring.
