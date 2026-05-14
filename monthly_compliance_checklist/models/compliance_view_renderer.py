# -*- coding: utf-8 -*-

from odoo import api, models


class ComplianceViewRenderer(models.TransientModel):
    """
    Utility model for rendering dynamic compliance check views.
    Used by check templates to show appropriate UI based on selected check type.
    """

    _name = "compliance.view.renderer"
    _description = "Compliance View Renderer"

    @api.model
    def get_check_type_view(self, check_type, view_type="form"):
        """
        Get the custom view definition for a specific check type.

        Args:
            check_type (str): The compliance check type key
            view_type (str): Type of view ('form', 'tree', 'search')

        Returns:
            str: XML view definition or None if not found
        """
        # Find the model that implements this check type
        for model_name in self.env.registry:
            model_class = self.env.registry[model_name]
            if (
                hasattr(model_class, "_compliance_check_type")
                and model_class._compliance_check_type == check_type
            ):

                # Get the model instance to call the view method
                model_instance = self.env[model_name]
                return model_instance.get_dynamic_view(view_type)

        return None

    @api.model
    def validate_check_type_configuration(self, check_type, values):
        """
        Validate configuration values for a specific check type.

        Args:
            check_type (str): The compliance check type key
            values (dict): Field values to validate

        Returns:
            dict: {'valid': bool, 'errors': list, 'warnings': list}
        """
        validation_result = {"valid": True, "errors": [], "warnings": []}

        # Find the model that implements this check type
        for model_name in self.env.registry:
            model_class = self.env.registry[model_name]
            if (
                hasattr(model_class, "_compliance_check_type")
                and model_class._compliance_check_type == check_type
            ):

                # Get the model instance to perform validation
                model_instance = self.env[model_name]

                # Check required fields specific to this check type
                evaluation_fields = model_instance.get_evaluation_fields()
                for field_name in evaluation_fields:
                    field_info = model_instance._fields.get(field_name)
                    if field_info and getattr(field_info, "required", False):
                        if field_name not in values or not values[field_name]:
                            validation_result["errors"].append(
                                f"Field '{field_info.string}' is required for {check_type} checks"
                            )
                            validation_result["valid"] = False

                # Perform check-type specific validation
                if hasattr(model_instance, "validate_configuration"):
                    check_validation = model_instance.validate_configuration(values)
                    if check_validation:
                        validation_result["errors"].extend(
                            check_validation.get("errors", [])
                        )
                        validation_result["warnings"].extend(
                            check_validation.get("warnings", [])
                        )
                        if check_validation.get("errors"):
                            validation_result["valid"] = False

                break

        return validation_result

    @api.model
    def get_check_type_help_text(self, check_type):
        """
        Get help text and examples for a specific check type.

        Args:
            check_type (str): The compliance check type key

        Returns:
            dict: {'description': str, 'examples': list, 'tips': list}
        """
        help_data = {
            "partner_payment": {
                "description": "Validates that specific partners have made expected payments within the period.",
                "examples": [
                    "Monthly rent payment from landlord",
                    "Quarterly insurance premium payments",
                    "Weekly contractor payments",
                ],
                "tips": [
                    "Use amount tolerance for payments that may vary slightly",
                    "Enable reconciliation requirement for critical payments",
                    "Set payment frequency to match business requirements",
                ],
            },
            "attachment_check": {
                "description": "Ensures transactions have required attachments with specific file criteria.",
                "examples": [
                    "All vendor bills must have PDF invoices attached",
                    "Expense transactions require receipt images",
                    "Large transactions need supporting documentation",
                ],
                "tips": [
                    "Use filename patterns to enforce naming conventions",
                    "Set file size limits to ensure quality and prevent abuse",
                    "Choose between requiring all transactions vs. any transaction",
                ],
            },
        }

        return help_data.get(
            check_type,
            {"description": "Custom compliance check type", "examples": [], "tips": []},
        )

    @api.model
    def get_available_check_types_with_info(self):
        """
        Get all available check types with their detailed information.

        Returns:
            list: [{'key': str, 'name': str, 'description': str, 'model': str}, ...]
        """
        check_types = []

        for model_name in self.env.registry:
            model_class = self.env.registry[model_name]
            if hasattr(model_class, "_compliance_check_type") and hasattr(
                model_class, "_compliance_check_name"
            ):

                help_info = self.get_check_type_help_text(
                    model_class._compliance_check_type
                )

                check_types.append(
                    {
                        "key": model_class._compliance_check_type,
                        "name": model_class._compliance_check_name,
                        "description": help_info.get("description", ""),
                        "model": model_name,
                        "examples": help_info.get("examples", []),
                        "tips": help_info.get("tips", []),
                    }
                )

        return sorted(check_types, key=lambda x: x["name"])
