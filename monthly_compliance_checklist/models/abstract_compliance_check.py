# -*- coding: utf-8 -*-

from odoo import models, fields, api
import calendar


class AbstractComplianceCheck(models.AbstractModel):
    """
    Abstract base model for all compliance check types.
    Each specific check type inherits from this and implements its own evaluation logic.
    """
    _name = 'abstract.compliance.check'
    _description = 'Abstract Compliance Check'
    
    # Base fields common to all check types
    name = fields.Char(string='Check Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Validity period
    valid_from = fields.Date(
        string='Valid From',
        help='Date when this check becomes effective (leave empty for no start limit)'
    )
    valid_until = fields.Date(
        string='Valid Until', 
        help='Date when this check expires (leave empty for perpetual)'
    )
    
    @classmethod
    def get_registered_check_types(cls, env):
        """
        Return all available compliance check types from registered models.
        Returns: list of tuples [(type_key, display_name), ...]
        """
        check_types = []
        for model_name in env.registry:
            model_class = env.registry[model_name]
            if (hasattr(model_class, '_compliance_check_type') and 
                hasattr(model_class, '_compliance_check_name')):
                check_types.append((
                    model_class._compliance_check_type,
                    model_class._compliance_check_name
                ))
        
        # Sort by display name for better UX
        return sorted(check_types, key=lambda x: x[1])
    
    def is_applicable_for_month(self, year, month):
        """
        Determine if this check should be active for the given month/year.
        Returns: bool
        """
        from datetime import date
        check_date = date(year, month, 1)
        
        # Check start date
        if self.valid_from and check_date < self.valid_from:
            return False
            
        # Check end date  
        if self.valid_until and check_date > self.valid_until:
            return False
            
        return True
    
    def evaluate_condition(self, year, month):
        """
        Abstract method - must be implemented by each check type.
        Evaluates if this check passes for the given month/year.
        
        Args:
            year (int): Year to evaluate
            month (int): Month to evaluate
            
        Returns:
            tuple: (is_met: bool, details: dict)
        """
        raise NotImplementedError("Each compliance check type must implement evaluate_condition()")
    
    def create_check_instance(self, checklist_id):
        """
        Create a check instance for this template in a monthly checklist.
        Returns: check.instance record
        """
        return self.env['check.instance'].create({
            'name': self.name,
            'template_id': self.id,
            'template_model': self._name,
            'checklist_id': checklist_id,
            'sequence': self.sequence,
        })
    
    def _get_month_date_range(self, year, month):
        """
        Helper method to get start and end dates for a given month.
        Returns: tuple (start_date, end_date)
        """
        from datetime import date
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        return start_date, end_date
    
    @api.model
    def get_evaluation_fields(self):
        """
        Return list of field names that are relevant for this check type's evaluation.
        Used by UI to show only relevant fields in forms.
        Override in subclasses to specify which fields are used.
        """
        return ['name', 'sequence', 'valid_from', 'valid_until']
    
    @classmethod
    def get_view_ids(cls, env):
        """
        Return view IDs for this check type.
        Override in subclasses to provide specialized view references.
        
        Returns:
            dict: {
                'form': view_id,
                'tree': view_id,
                'search': view_id,
                'action': action_id
            }
        """
        return {}
    
    @api.model
    def get_configuration_action(self):
        """
        Return action to open this check type's configuration.
        Override in subclasses to provide specialized configuration UI.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self._compliance_check_name} Configuration',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
        }
    
    @api.model
    def create(self, vals):
        """Override create to link back to template if context provided"""
        record = super().create(vals)
        
        # If created from a template, link it back
        template_id = self.env.context.get('template_id')
        if template_id:
            template = self.env['check.template'].browse(template_id)
            template.compliance_check_id = f"{self._name},{record.id}"
        
        return record