# models/ledger_credit_debit.py
"""
Ledger Credit/Debit Model - Double-Entry Accounting Lines
"""

from typing import Optional, Dict, List
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class LedgerCreditDebit:
    """Ledger Credit/Debit model for double-entry accounting lines"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_table(self) -> bool:
        """Create ledger credit/debit table"""
        query = '''
            CREATE TABLE IF NOT EXISTS ledger_credit_debit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR(10) NOT NULL,
                number VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                acct_code VARCHAR(50) NOT NULL,
                acct_description VARCHAR(255) NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                acct_type VARCHAR(1) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (number) REFERENCES ledger (number)
            )
        '''
        return self.db.execute_query(query)
    
    def create(self, entry_type: str, number: str, entry_date: date, 
               acct_code: str, acct_description: str, amount: float, 
               acct_type: str) -> Optional[int]:
        """Create a new credit/debit entry"""
        
        # Validate acct_type
        if acct_type not in ['D', 'C']:
            logger.error(f"Invalid acct_type: {acct_type}. Must be 'D' or 'C'")
            return None
        
        query = '''
            INSERT INTO ledger_credit_debit (type, number, date, acct_code, 
                                           acct_description, amount, acct_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    entry_type, number, entry_date, acct_code, 
                    acct_description, amount, acct_type
                ))
                entry_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Credit/Debit entry created: {number} - {acct_code} - {acct_type} ${amount}")
                return entry_id
        except Exception as e:
            logger.error(f"Failed to create credit/debit entry for {number}: {e}")
            return None
    
    def create_multiple(self, entries: List[Dict]) -> bool:
        """Create multiple credit/debit entries in a transaction"""
        if not entries:
            return False
        
        query = '''
            INSERT INTO ledger_credit_debit (type, number, date, acct_code, 
                                           acct_description, amount, acct_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                for entry in entries:
                    # Validate each entry
                    if entry.get('acct_type') not in ['D', 'C']:
                        logger.error(f"Invalid acct_type in entry: {entry}")
                        conn.rollback()
                        return False
                    
                    cursor.execute(query, (
                        entry['type'], entry['number'], entry['date'], 
                        entry['acct_code'], entry['acct_description'], 
                        entry['amount'], entry['acct_type']
                    ))
                
                conn.commit()
                logger.info(f"Created {len(entries)} credit/debit entries for {entries[0]['number']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create multiple credit/debit entries: {e}")
            return False
    
    def get_by_id(self, entry_id: int) -> Optional[Dict]:
        """Get credit/debit entry by ID"""
        query = '''
            SELECT * FROM ledger_credit_debit WHERE id = ?
        '''
        return self.db.fetch_one(query, (entry_id,))
    
    def get_by_number(self, number: str) -> List[Dict]:
        """Get all credit/debit entries for a ledger number"""
        query = '''
            SELECT * FROM ledger_credit_debit 
            WHERE number = ? 
            ORDER BY acct_type, acct_code
        '''
        return self.db.fetch_all(query, (number,))
    
    def get_by_account(self, acct_code: str, start_date: date = None, 
                      end_date: date = None) -> List[Dict]:
        """Get credit/debit entries for a specific account"""
        query = '''
            SELECT lcd.*, l.payee, l.description as ledger_description
            FROM ledger_credit_debit lcd
            JOIN ledger l ON lcd.number = l.number
            WHERE lcd.acct_code = ?
        '''
        params = [acct_code]
        
        if start_date:
            query += " AND lcd.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND lcd.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY lcd.date DESC, lcd.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_by_type(self, entry_type: str, start_date: date = None, 
                   end_date: date = None) -> List[Dict]:
        """Get credit/debit entries by type (VP or CV)"""
        query = '''
            SELECT lcd.*, l.payee, l.description as ledger_description
            FROM ledger_credit_debit lcd
            JOIN ledger l ON lcd.number = l.number
            WHERE lcd.type = ?
        '''
        params = [entry_type]
        
        if start_date:
            query += " AND lcd.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND lcd.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY lcd.date DESC, lcd.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_debits(self, acct_code: str = None, start_date: date = None, 
                  end_date: date = None) -> List[Dict]:
        """Get debit entries"""
        query = '''
            SELECT lcd.*, l.payee, l.description as ledger_description
            FROM ledger_credit_debit lcd
            JOIN ledger l ON lcd.number = l.number
            WHERE lcd.acct_type = 'D'
        '''
        params = []
        
        if acct_code:
            query += " AND lcd.acct_code = ?"
            params.append(acct_code)
        
        if start_date:
            query += " AND lcd.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND lcd.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY lcd.date DESC, lcd.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_credits(self, acct_code: str = None, start_date: date = None, 
                   end_date: date = None) -> List[Dict]:
        """Get credit entries"""
        query = '''
            SELECT lcd.*, l.payee, l.description as ledger_description
            FROM ledger_credit_debit lcd
            JOIN ledger l ON lcd.number = l.number
            WHERE lcd.acct_type = 'C'
        '''
        params = []
        
        if acct_code:
            query += " AND lcd.acct_code = ?"
            params.append(acct_code)
        
        if start_date:
            query += " AND lcd.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND lcd.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY lcd.date DESC, lcd.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def update(self, entry_id: int, **kwargs) -> bool:
        """Update credit/debit entry fields"""
        allowed_fields = ['acct_code', 'acct_description', 'amount', 'acct_type']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Validate acct_type if being updated
        if 'acct_type' in updates and updates['acct_type'] not in ['D', 'C']:
            logger.error(f"Invalid acct_type: {updates['acct_type']}")
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE ledger_credit_debit 
            SET {set_clause}
            WHERE id = ?
        '''
        
        values = list(updates.values()) + [entry_id]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"Credit/Debit entry {entry_id} updated: {updates}")
        return success
    
    def delete(self, entry_id: int) -> bool:
        """Delete credit/debit entry"""
        query = 'DELETE FROM ledger_credit_debit WHERE id = ?'
        success = self.db.execute_query(query, (entry_id,))
        if success:
            logger.info(f"Credit/Debit entry {entry_id} deleted")
        return success
    
    def delete_by_number(self, number: str) -> bool:
        """Delete all credit/debit entries for a ledger number"""
        query = 'DELETE FROM ledger_credit_debit WHERE number = ?'
        success = self.db.execute_query(query, (number,))
        if success:
            logger.info(f"All credit/debit entries deleted for ledger {number}")
        return success
    
    def validate_entry_balance(self, number: str) -> Dict:
        """Validate that debits equal credits for a ledger entry"""
        query = '''
            SELECT 
                SUM(CASE WHEN acct_type = 'D' THEN amount ELSE 0 END) as total_debits,
                SUM(CASE WHEN acct_type = 'C' THEN amount ELSE 0 END) as total_credits
            FROM ledger_credit_debit
            WHERE number = ?
        '''
        
        result = self.db.fetch_one(query, (number,))
        
        if result:
            total_debits = float(result['total_debits'] or 0)
            total_credits = float(result['total_credits'] or 0)
            difference = abs(total_debits - total_credits)
            
            return {
                'balanced': difference < 0.01,  # Allow for small rounding differences
                'total_debits': total_debits,
                'total_credits': total_credits,
                'difference': difference
            }
        
        return {
            'balanced': False,
            'total_debits': 0,
            'total_credits': 0,
            'difference': 0
        }
    
    def get_account_balance(self, acct_code: str, as_of_date: date = None) -> Dict:
        """Get account balance (debits - credits)"""
        query = '''
            SELECT 
                SUM(CASE WHEN acct_type = 'D' THEN amount ELSE 0 END) as total_debits,
                SUM(CASE WHEN acct_type = 'C' THEN amount ELSE 0 END) as total_credits
            FROM ledger_credit_debit
            WHERE acct_code = ?
        '''
        params = [acct_code]
        
        if as_of_date:
            query += " AND date <= ?"
            params.append(as_of_date)
        
        result = self.db.fetch_one(query, tuple(params))
        
        if result:
            total_debits = float(result['total_debits'] or 0)
            total_credits = float(result['total_credits'] or 0)
            balance = total_debits - total_credits
            
            return {
                'acct_code': acct_code,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'balance': balance,
                'as_of_date': as_of_date or date.today()
            }
        
        return {
            'acct_code': acct_code,
            'total_debits': 0,
            'total_credits': 0,
            'balance': 0,
            'as_of_date': as_of_date or date.today()
        }
    
    def get_trial_balance(self, as_of_date: date = None) -> List[Dict]:
        """Get trial balance for all accounts"""
        query = '''
            SELECT 
                acct_code,
                acct_description,
                SUM(CASE WHEN acct_type = 'D' THEN amount ELSE 0 END) as total_debits,
                SUM(CASE WHEN acct_type = 'C' THEN amount ELSE 0 END) as total_credits
            FROM ledger_credit_debit
        '''
        params = []
        
        if as_of_date:
            query += " WHERE date <= ?"
            params.append(as_of_date)
        
        query += '''
            GROUP BY acct_code, acct_description
            HAVING (total_debits != 0 OR total_credits != 0)
            ORDER BY acct_code
        '''
        
        results = self.db.fetch_all(query, tuple(params))
        
        trial_balance = []
        for result in results:
            total_debits = float(result['total_debits'] or 0)
            total_credits = float(result['total_credits'] or 0)
            balance = total_debits - total_credits
            
            trial_balance.append({
                'acct_code': result['acct_code'],
                'acct_description': result['acct_description'],
                'total_debits': total_debits,
                'total_credits': total_credits,
                'balance': balance
            })
        
        return trial_balance
    
    def get_account_activity(self, acct_code: str, start_date: date = None, 
                           end_date: date = None, limit: int = 100) -> List[Dict]:
        """Get detailed account activity"""
        query = '''
            SELECT 
                lcd.*,
                l.payee,
                l.description as ledger_description,
                l.status
            FROM ledger_credit_debit lcd
            JOIN ledger l ON lcd.number = l.number
            WHERE lcd.acct_code = ?
        '''
        params = [acct_code]
        
        if start_date:
            query += " AND lcd.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND lcd.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY lcd.date DESC, lcd.number DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_statistics(self) -> Dict:
        """Get credit/debit statistics"""
        try:
            stats = {}
            
            # Total entries
            result = self.db.fetch_one('SELECT COUNT(*) as count FROM ledger_credit_debit')
            stats['total_entries'] = result['count'] if result else 0
            
            # By type
            result = self.db.fetch_all('''
                SELECT acct_type, COUNT(*) as count, SUM(amount) as total_amount
                FROM ledger_credit_debit
                GROUP BY acct_type
            ''')
            stats['by_acct_type'] = {
                row['acct_type']: {
                    'count': row['count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in result
            }
            
            # By transaction type
            result = self.db.fetch_all('''
                SELECT type, COUNT(*) as count, SUM(amount) as total_amount
                FROM ledger_credit_debit
                GROUP BY type
            ''')
            stats['by_transaction_type'] = {
                row['type']: {
                    'count': row['count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in result
            }
            
            # Most active accounts
            result = self.db.fetch_all('''
                SELECT acct_code, acct_description, COUNT(*) as transaction_count,
                       SUM(amount) as total_amount
                FROM ledger_credit_debit
                GROUP BY acct_code, acct_description
                ORDER BY transaction_count DESC
                LIMIT 10
            ''')
            stats['most_active_accounts'] = [
                {
                    'acct_code': row['acct_code'],
                    'acct_description': row['acct_description'],
                    'transaction_count': row['transaction_count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in result
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting credit/debit statistics: {e}")
            return {}