# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChecklistItem(models.Model):
    _name = 'checklist.item'
    _description = 'Checklist Item'
    _order = 'checklist_id, sequence, name'

    name = fields.Char(string='Item Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    checklist_id = fields.Many2one(
        'monthly.checklist',
        string='Checklist',
        required=True,
        ondelete='cascade'
    )
    
    # Item configuration
    item_type = fields.Selection([
        ('account', 'Account Transaction'),
        ('partner', 'Partner Transaction')
    ], string='Item Type', required=True, default='account')
    
    required_transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('any', 'Any')
    ], string='Transaction Type', default='any')
    
    # Related fields
    account_id = fields.Many2one('account.account', string='Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    
    # Status tracking
    is_completed = fields.Boolean(
        string='Completed',
        compute='_compute_is_completed',
        store=True
    )
    completion_date = fields.Datetime(string='Completion Date')
    notes = fields.Text(string='Notes')
    
    # Template item reference for automated validation
    template_item_id = fields.Many2one(
        'compliance.template.item',
        string='Template Item',
        help='Reference to the template item this checklist item was created from'
    )
    
    # Validation details
    validation_message = fields.Text(
        string='Validation Details',
        help='Details about condition evaluation'
    )
    
    # Debug field to show search criteria
    debug_info = fields.Text(
        string='Debug Info',
        compute='_compute_debug_info',
        help='Debug information about search criteria'
    )
    
    # Transaction tracking
    related_moves = fields.Many2many(
        'account.move',
        string='Related Transactions',
        compute='_compute_related_moves'
    )
    transaction_count = fields.Integer(
        string='Transaction Count',
        compute='_compute_transaction_count'
    )
    
    @api.depends('checklist_id.year', 'checklist_id.month', 'account_id', 'partner_id', 'item_type', 'required_transaction_type')
    def _compute_related_moves(self):
        """Find transactions that satisfy this checklist item"""
        import logging
        _logger = logging.getLogger(__name__)
        
        for item in self:
            domain = [
                ('state', '=', 'posted')
            ]
            
            # Date filter for the checklist month
            if item.checklist_id.year and item.checklist_id.month:
                year = item.checklist_id.year
                month = item.checklist_id.month
                
                # First day of month
                start_date = fields.Date.from_string(f"{year}-{month:02d}-01")
                
                # Last day of month
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                end_date = fields.Date.from_string(f"{year}-{month:02d}-{last_day}")
                
                domain.extend([
                    ('date', '>=', start_date),
                    ('date', '<=', end_date)
                ])
                
                print(f"CONSOLE: Item '{item.name}' searching for transactions between {start_date} and {end_date}")
                _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' searching for transactions between {start_date} and {end_date}")
            
            # Filter by account
            if item.item_type == 'account' and item.account_id:
                domain.append(('line_ids.account_id', '=', item.account_id.id))
                print(f"CONSOLE: Item '{item.name}' filtering by account: {item.account_id.name} (ID: {item.account_id.id})")
                _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' filtering by account: {item.account_id.name} (ID: {item.account_id.id})")
                
                # Filter by transaction type if specified
                if item.required_transaction_type == 'income':
                    domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
                    print(f"CONSOLE: Item '{item.name}' filtering for income transaction types: out_invoice, out_refund")
                    _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' filtering for income transaction types: out_invoice, out_refund")
                elif item.required_transaction_type == 'expense':
                    domain.append(('move_type', 'in', ['in_invoice', 'in_refund', 'entry']))
                    print(f"CONSOLE: Item '{item.name}' filtering for expense transaction types: in_invoice, in_refund, entry")
                    _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' filtering for expense transaction types: in_invoice, in_refund, entry")
            
            # Filter by partner
            elif item.item_type == 'partner' and item.partner_id:
                domain.append(('partner_id', '=', item.partner_id.id))
                print(f"CONSOLE: Item '{item.name}' filtering by partner: {item.partner_id.name} (ID: {item.partner_id.id})")
                _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' filtering by partner: {item.partner_id.name} (ID: {item.partner_id.id})")
            
            print(f"CONSOLE: Item '{item.name}' final search domain: {domain}")
            _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' final search domain: {domain}")
            
            moves = self.env['account.move'].search(domain)
            print(f"CONSOLE: Item '{item.name}' found {len(moves)} matching transactions: {[f'{m.name} ({m.partner_id.name if m.partner_id else \"No Partner\"})' for m in moves]}")
            _logger.warning(f"[CHECKLIST DEBUG] Item '{item.name}' found {len(moves)} matching transactions: {[f'{m.name} ({m.partner_id.name if m.partner_id else \"No Partner\"})' for m in moves]}")
            
            item.related_moves = [(6, 0, moves.ids)]
    
    @api.depends('related_moves')
    def _compute_transaction_count(self):
        for item in self:
            item.transaction_count = len(item.related_moves)
    
    @api.depends('checklist_id.year', 'checklist_id.month', 'account_id', 'partner_id', 'item_type', 'required_transaction_type')
    def _compute_debug_info(self):
        """Show debug information about search criteria"""
        for item in self:
            debug_lines = []
            debug_lines.append(f"=== DEBUG INFO FOR {item.name} ===")
            debug_lines.append(f"Item Type: {item.item_type}")
            debug_lines.append(f"Required Transaction Type: {item.required_transaction_type}")
            debug_lines.append(f"Checklist Year: {item.checklist_id.year}")
            debug_lines.append(f"Checklist Month: {item.checklist_id.month}")
            
            if item.partner_id:
                debug_lines.append(f"Partner: {item.partner_id.name} (ID: {item.partner_id.id})")
            if item.account_id:
                debug_lines.append(f"Account: {item.account_id.name} (ID: {item.account_id.id})")
            
            # Build the same domain as in _compute_related_moves
            domain = [('state', '=', 'posted')]
            
            if item.checklist_id.year and item.checklist_id.month:
                year = item.checklist_id.year
                month = item.checklist_id.month
                
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day}"
                
                domain.extend([
                    ('date', '>=', start_date),
                    ('date', '<=', end_date)
                ])
                debug_lines.append(f"Date Range: {start_date} to {end_date}")
            
            if item.item_type == 'account' and item.account_id:
                domain.append(('line_ids.account_id', '=', item.account_id.id))
                if item.required_transaction_type == 'income':
                    domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
                    debug_lines.append("Transaction Types: out_invoice, out_refund")
                elif item.required_transaction_type == 'expense':
                    domain.append(('move_type', 'in', ['in_invoice', 'in_refund', 'entry']))
                    debug_lines.append("Transaction Types: in_invoice, in_refund, entry")
            elif item.item_type == 'partner' and item.partner_id:
                domain.append(('partner_id', '=', item.partner_id.id))
            
            debug_lines.append(f"Search Domain: {domain}")
            
            # Count transactions that would match
            try:
                moves = self.env['account.move'].search(domain)
                debug_lines.append(f"Transactions Found: {len(moves)}")
                if moves:
                    for move in moves[:5]:  # Show first 5
                        debug_lines.append(f"  - {move.name} ({move.date}) - {move.partner_id.name if move.partner_id else 'No Partner'}")
                    if len(moves) > 5:
                        debug_lines.append(f"  ... and {len(moves) - 5} more")
            except Exception as e:
                debug_lines.append(f"Error searching: {e}")
            
            item.debug_info = '\n'.join(debug_lines)
    
    @api.depends('item_type', 'transaction_count', 'template_item_id')
    def _compute_is_completed(self):
        """Determine if item is completed based on transactions or template conditions"""
        for item in self:
            if item.template_item_id:
                # Use template item condition evaluation
                is_met, details = item.template_item_id.evaluate_condition(
                    item.checklist_id.year, 
                    item.checklist_id.month
                )
                was_completed = item.is_completed
                item.is_completed = is_met
                item.validation_message = details.get('message', '')
                
                # Set completion date when first completed
                if is_met and not was_completed:
                    item.completion_date = fields.Datetime.now()
                elif not is_met and item.completion_date:
                    item.completion_date = False
                    
            # No manual items - all are automated
            else:
                # Account/partner items are completed when they have transactions
                was_completed = item.is_completed
                item.is_completed = item.transaction_count > 0
                
                # Set completion date when first completed
                if item.is_completed and not was_completed:
                    item.completion_date = fields.Datetime.now()
    
    def reevaluate_condition(self):
        """Manually trigger condition re-evaluation"""
        import logging
        _logger = logging.getLogger(__name__)
        
        # Try multiple logging approaches
        print(f"=== CONSOLE: MANUAL REEVALUATE FOR {self.name} ===")
        _logger.error(f"[CHECKLIST DEBUG] === MANUAL REEVALUATE FOR {self.name} ===")
        _logger.warning(f"[CHECKLIST DEBUG] === MANUAL REEVALUATE FOR {self.name} ===")
        _logger.info(f"[CHECKLIST DEBUG] === MANUAL REEVALUATE FOR {self.name} ===")
        
        print(f"CONSOLE: Item type: {self.item_type}")
        print(f"CONSOLE: Partner: {self.partner_id.name if self.partner_id else 'None'} (ID: {self.partner_id.id if self.partner_id else 'None'})")
        print(f"CONSOLE: Account: {self.account_id.name if self.account_id else 'None'} (ID: {self.account_id.id if self.account_id else 'None'})")
        print(f"CONSOLE: Required transaction type: {self.required_transaction_type}")
        print(f"CONSOLE: Checklist year: {self.checklist_id.year}")
        print(f"CONSOLE: Checklist month: {self.checklist_id.month}")
        
        self._compute_related_moves()
        self._compute_is_completed()
        print(f"CONSOLE: Reevaluation complete for item: {self.name}")
    
    def debug_search_criteria(self):
        """Debug action to show search criteria"""
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"[CHECKLIST DEBUG] === DEBUG SEARCH CRITERIA FOR {self.name} ===")
        _logger.warning(f"[CHECKLIST DEBUG] Item type: {self.item_type}")
        _logger.warning(f"[CHECKLIST DEBUG] Partner: {self.partner_id.name if self.partner_id else 'None'} (ID: {self.partner_id.id if self.partner_id else 'None'})")
        _logger.warning(f"[CHECKLIST DEBUG] Account: {self.account_id.name if self.account_id else 'None'} (ID: {self.account_id.id if self.account_id else 'None'})")
        _logger.warning(f"[CHECKLIST DEBUG] Required transaction type: {self.required_transaction_type}")
        _logger.warning(f"[CHECKLIST DEBUG] Checklist year: {self.checklist_id.year}")
        _logger.warning(f"[CHECKLIST DEBUG] Checklist month: {self.checklist_id.month}")
        
        # Force recomputation
        self._compute_related_moves()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Debug Complete',
                'message': f'Check logs for debug info about {self.name}',
                'type': 'info'
            }
        }
    
    def action_mark_complete(self):
        """Manually mark item as complete (for manual items)"""
        self.completion_date = fields.Datetime.now()
        self.message_post(body="Item manually marked as complete")
    
    def action_mark_incomplete(self):
        """Manually mark item as incomplete"""
        self.completion_date = False
        self.message_post(body="Item marked as incomplete")
    
    def action_view_transactions(self):
        """Open related transactions"""
        return {
            'name': f'Transactions for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.related_moves.ids)],
            'context': {'default_partner_id': self.partner_id.id if self.partner_id else False}
        }