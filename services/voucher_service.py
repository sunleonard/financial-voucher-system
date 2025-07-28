# services/voucher_service.py
"""
Voucher Service - Business logic for voucher management using new accounting ledger structure
"""

from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)

class VoucherService:
    """Voucher management service using double-entry accounting"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_voucher_payable(self, payee_code: str, payee: str, total_amount: Decimal,
                              description: str = None, due_date: str = None,
                              line_items: List[Dict] = None, created_by: int = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new Voucher Payable with double-entry accounting
        
        Args:
            payee_code: Account code of the payee
            payee: Name of the payee
            total_amount: Total amount of the voucher
            description: Description of the voucher
            due_date: Due date for payment
            line_items: List of line items with account codes and amounts
            created_by: User ID creating the voucher
        
        Returns:
            (success, message, voucher_number)
        """
        try:
            # Generate voucher number
            voucher_number = self._generate_voucher_number('VP')
            voucher_date = datetime.now().strftime('%Y-%m-%d')
            
            # Validate inputs
            if not payee_code or not payee or not total_amount:
                return False, "Payee code, payee name, and amount are required", None
            
            if not line_items:
                return False, "At least one line item is required", None
            
            # Validate line items sum to total
            line_items_total = sum(Decimal(str(item.get('amount', 0))) for item in line_items)
            if line_items_total != Decimal(str(total_amount)):
                return False, f"Line items total ({line_items_total}) must equal voucher total ({total_amount})", None
            
            # Start transaction
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert main ledger entry
                cursor.execute('''
                    INSERT INTO ledger (type, number, date, payee_code, payee, total_amount, 
                                      description, due_date, status, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                ''', ('VP', voucher_number, voucher_date, payee_code, payee, 
                      float(total_amount), description, due_date, created_by))
                
                # Insert credit entry (Accounts Payable - Credit side)
                cursor.execute('''
                    INSERT INTO ledger_credit_debit (type, number, date, acct_code, acct_description, 
                                                   amount, acct_type)
                    VALUES (?, ?, ?, ?, ?, ?, 'C')
                ''', ('VP', voucher_number, voucher_date, payee_code, payee, 
                      float(total_amount)))
                
                # Insert debit entries (Expense accounts - Debit side)
                for item in line_items:
                    cursor.execute('''
                        INSERT INTO ledger_credit_debit (type, number, date, acct_code, acct_description, 
                                                       amount, acct_type)
                        VALUES (?, ?, ?, ?, ?, ?, 'D')
                    ''', ('VP', voucher_number, voucher_date, 
                          item['acct_code'], item['acct_description'], 
                          float(item['amount'])))
                    
                    # Insert subsidiary breakdown if provided
                    if item.get('subcodes'):
                        for subcode in item['subcodes']:
                            cursor.execute('''
                                INSERT INTO ledger_subcodes (type, number, date, acct_code, acct_description,
                                                           subsidiary_code, subsidiary_description, amount)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', ('VP', voucher_number, voucher_date,
                                  item['acct_code'], item['acct_description'],
                                  subcode['code'], subcode['description'], 
                                  float(subcode['amount'])))
                
                conn.commit()
                
                # Log audit trail
                from services.audit_service import AuditService
                audit_service = AuditService(self.db)
                audit_service.log_action(
                    user_id=created_by,
                    action="CREATE_VOUCHER_PAYABLE",
                    table_name="ledger",
                    record_id=voucher_number,
                    new_values={
                        'type': 'VP',
                        'number': voucher_number,
                        'payee': payee,
                        'amount': float(total_amount)
                    }
                )
                
                logger.info(f"Voucher Payable {voucher_number} created for {payee}: ${total_amount}")
                return True, "Voucher Payable created successfully", voucher_number
                
        except Exception as e:
            logger.error(f"Error creating voucher payable: {e}")
            return False, f"Error creating voucher: {str(e)}", None
    
    def create_check_voucher(self, vp_number: str = None, payee_code: str = None, 
                           payee: str = None, amount: Decimal = None,
                           check_number: str = None, bank_account: str = None,
                           check_date: str = None, created_by: int = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a Check Voucher (payment against VP or standalone)
        
        Returns:
            (success, message, cv_number)
        """
        try:
            # Generate check voucher number
            cv_number = self._generate_voucher_number('CV')
            voucher_date = datetime.now().strftime('%Y-%m-%d')
            
            if vp_number:
                # Payment against existing VP
                vp_details = self.get_voucher_by_number(vp_number)
                if not vp_details:
                    return False, f"Voucher Payable {vp_number} not found", None
                
                payee_code = vp_details['payee_code']
                payee = vp_details['payee']
                if not amount:
                    amount = Decimal(str(vp_details['total_amount']))
            
            if not all([payee_code, payee, amount]):
                return False, "Payee code, payee name, and amount are required", None
            
            # Start transaction
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert main ledger entry
                cursor.execute('''
                    INSERT INTO ledger (type, number, date, payee_code, payee, total_amount, 
                                      description, status, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
                ''', ('CV', cv_number, voucher_date, payee_code, payee, 
                      float(amount), f"Check payment to {payee}", created_by))
                
                # Insert debit entry (Accounts Payable - Debit side to reduce liability)
                cursor.execute('''
                    INSERT INTO ledger_credit_debit (type, number, date, acct_code, acct_description, 
                                                   amount, acct_type)
                    VALUES (?, ?, ?, ?, ?, ?, 'D')
                ''', ('CV', cv_number, voucher_date, payee_code, payee, float(amount)))
                
                # Insert credit entry (Bank Account - Credit side)
                bank_code = bank_account or '1010'  # Default bank account
                cursor.execute('''
                    INSERT INTO ledger_credit_debit (type, number, date, acct_code, acct_description, 
                                                   amount, acct_type)
                    VALUES (?, ?, ?, ?, ?, ?, 'C')
                ''', ('CV', cv_number, voucher_date, bank_code, 
                      f"Bank Payment - Check #{check_number}", float(amount)))
                
                # Update VP status if applicable
                if vp_number:
                    cursor.execute('''
                        UPDATE ledger SET status = 'paid' WHERE number = ?
                    ''', (vp_number,))
                
                conn.commit()
                
                logger.info(f"Check Voucher {cv_number} created for {payee}: ${amount}")
                return True, "Check Voucher created successfully", cv_number
                
        except Exception as e:
            logger.error(f"Error creating check voucher: {e}")
            return False, f"Error creating check voucher: {str(e)}", None
    
    def get_voucher_by_number(self, voucher_number: str) -> Optional[Dict]:
        """Get voucher details by number"""
        try:
            query = '''
                SELECT * FROM ledger WHERE number = ?
            '''
            return self.db.fetch_one(query, (voucher_number,))
        except Exception as e:
            logger.error(f"Error getting voucher {voucher_number}: {e}")
            return None
    
    def get_voucher_details(self, voucher_number: str) -> Dict:
        """Get complete voucher details with line items"""
        try:
            # Get main voucher
            voucher = self.get_voucher_by_number(voucher_number)
            if not voucher:
                return {}
            
            # Get credit/debit entries
            line_items = self.db.fetch_all('''
                SELECT * FROM ledger_credit_debit 
                WHERE number = ? 
                ORDER BY acct_type DESC, acct_code
            ''', (voucher_number,))
            
            # Get subcodes
            subcodes = self.db.fetch_all('''
                SELECT * FROM ledger_subcodes 
                WHERE number = ?
                ORDER BY acct_code, subsidiary_code
            ''', (voucher_number,))
            
            return {
                'voucher': voucher,
                'line_items': line_items,
                'subcodes': subcodes
            }
        except Exception as e:
            logger.error(f"Error getting voucher details {voucher_number}: {e}")
            return {}
    
    def get_vouchers_list(self, voucher_type: str = None, status: str = None,
                         payee_code: str = None, created_by: int = None,
                         limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get list of vouchers with filters"""
        try:
            query = '''
                SELECT l.*, u.username as created_by_name
                FROM ledger l
                LEFT JOIN users u ON l.created_by = u.id
                WHERE 1=1
            '''
            params = []
            
            if voucher_type:
                query += ' AND l.type = ?'
                params.append(voucher_type)
            
            if status:
                query += ' AND l.status = ?'
                params.append(status)
            
            if payee_code:
                query += ' AND l.payee_code = ?'
                params.append(payee_code)
            
            if created_by:
                query += ' AND l.created_by = ?'
                params.append(created_by)
            
            query += ' ORDER BY l.date DESC, l.created_at DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
            
            if offset:
                query += ' OFFSET ?'
                params.append(offset)
            
            return self.db.fetch_all(query, tuple(params))
        except Exception as e:
            logger.error(f"Error getting vouchers list: {e}")
            return []
    
    def get_voucher_statistics(self, user_id: int = None) -> Dict:
        """Get voucher statistics"""
        try:
            stats = {}
            
            # Base query conditions
            where_clause = "WHERE 1=1"
            params = []
            
            if user_id:
                where_clause += " AND created_by = ?"
                params = [user_id]
            
            # Vouchers Payable stats
            vp_stats = self.db.fetch_one(f'''
                SELECT 
                    COUNT(*) as total_count,
                    SUM(total_amount) as total_amount,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as pending_count,
                    SUM(CASE WHEN status = 'active' THEN total_amount ELSE 0 END) as pending_amount
                FROM ledger
                {where_clause} AND type = 'VP'
            ''', tuple(params))
            
            stats['vouchers_payable'] = {
                'total_count': vp_stats['total_count'] or 0,
                'total_amount': float(vp_stats['total_amount'] or 0),
                'pending_count': vp_stats['pending_count'] or 0,
                'pending_amount': float(vp_stats['pending_amount'] or 0)
            }
            
            # Check Vouchers stats
            cv_stats = self.db.fetch_one(f'''
                SELECT 
                    COUNT(*) as total_count,
                    SUM(total_amount) as total_amount
                FROM ledger
                {where_clause} AND type = 'CV'
            ''', tuple(params))
            
            stats['check_vouchers'] = {
                'total_count': cv_stats['total_count'] or 0,
                'total_amount': float(cv_stats['total_amount'] or 0)
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting voucher statistics: {e}")
            return {}
    
    def _generate_voucher_number(self, voucher_type: str) -> str:
        """Generate next voucher number"""
        try:
            current_year = datetime.now().year
            
            # Get the highest number for this type and year
            result = self.db.fetch_one('''
                SELECT number FROM ledger 
                WHERE type = ? AND strftime('%Y', date) = ?
                ORDER BY number DESC LIMIT 1
            ''', (voucher_type, str(current_year)))
            
            if result:
                # Extract sequence number and increment
                parts = result['number'].split('-')
                if len(parts) == 3 and parts[1] == str(current_year):
                    sequence = int(parts[2]) + 1
                else:
                    sequence = 1
            else:
                sequence = 1
            
            return f"{voucher_type}-{current_year}-{sequence:03d}"
            
        except Exception as e:
            logger.error(f"Error generating voucher number: {e}")
            return f"{voucher_type}-{datetime.now().year}-001"
    
    def get_account_codes(self, acct_type: str = None) -> List[Dict]:
        """Get available account codes"""
        try:
            query = '''
                SELECT acct_code, acct_description, acct_type, acct_prefix
                FROM acct_definition
                WHERE is_active = 1
            '''
            params = []
            
            if acct_type:
                query += ' AND acct_type = ?'
                params.append(acct_type)
            
            query += ' ORDER BY acct_code'
            
            return self.db.fetch_all(query, tuple(params))
        except Exception as e:
            logger.error(f"Error getting account codes: {e}")
            return []
    
    def search_vouchers(self, search_term: str, voucher_type: str = None) -> List[Dict]:
        """Search vouchers by number, payee, or description"""
        try:
            query = '''
                SELECT l.*, u.username as created_by_name
                FROM ledger l
                LEFT JOIN users u ON l.created_by = u.id
                WHERE (l.number LIKE ? OR l.payee LIKE ? OR l.description LIKE ?)
            '''
            params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']
            
            if voucher_type:
                query += ' AND l.type = ?'
                params.append(voucher_type)
            
            query += ' ORDER BY l.date DESC'
            
            return self.db.fetch_all(query, tuple(params))
        except Exception as e:
            logger.error(f"Error searching vouchers: {e}")
            return []