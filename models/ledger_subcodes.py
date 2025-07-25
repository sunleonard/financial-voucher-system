# models/ledger_subcodes.py
"""
Ledger Subcodes Model - Subsidiary/Subcode Breakdown
"""

from typing import Optional, Dict, List
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class LedgerSubcodes:
    """Ledger Subcodes model for subsidiary breakdown of transactions"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_table(self) -> bool:
        """Create ledger subcodes table"""
        query = '''
            CREATE TABLE IF NOT EXISTS ledger_subcodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR(10) NOT NULL,
                number VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                acct_code VARCHAR(50) NOT NULL,
                acct_description VARCHAR(255) NOT NULL,
                subsidiary_code VARCHAR(50) NOT NULL,
                subsidiary_description VARCHAR(255) NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (number) REFERENCES ledger (number)
            )
        '''
        return self.db.execute_query(query)
    
    def create(self, entry_type: str, number: str, entry_date: date, 
               acct_code: str, acct_description: str, subsidiary_code: str,
               subsidiary_description: str, amount: float) -> Optional[int]:
        """Create a new subcode entry"""
        
        query = '''
            INSERT INTO ledger_subcodes (type, number, date, acct_code, acct_description,
                                       subsidiary_code, subsidiary_description, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    entry_type, number, entry_date, acct_code, acct_description,
                    subsidiary_code, subsidiary_description, amount
                ))
                entry_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Subcode entry created: {number} - {subsidiary_code} - ${amount}")
                return entry_id
        except Exception as e:
            logger.error(f"Failed to create subcode entry for {number}: {e}")
            return None
    
    def create_multiple(self, entries: List[Dict]) -> bool:
        """Create multiple subcode entries in a transaction"""
        if not entries:
            return False
        
        query = '''
            INSERT INTO ledger_subcodes (type, number, date, acct_code, acct_description,
                                       subsidiary_code, subsidiary_description, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                for entry in entries:
                    cursor.execute(query, (
                        entry['type'], entry['number'], entry['date'], 
                        entry['acct_code'], entry['acct_description'],
                        entry['subsidiary_code'], entry['subsidiary_description'],
                        entry['amount']
                    ))
                
                conn.commit()
                logger.info(f"Created {len(entries)} subcode entries for {entries[0]['number']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create multiple subcode entries: {e}")
            return False
    
    def get_by_id(self, entry_id: int) -> Optional[Dict]:
        """Get subcode entry by ID"""
        query = '''
            SELECT * FROM ledger_subcodes WHERE id = ?
        '''
        return self.db.fetch_one(query, (entry_id,))
    
    def get_by_number(self, number: str) -> List[Dict]:
        """Get all subcode entries for a ledger number"""
        query = '''
            SELECT * FROM ledger_subcodes 
            WHERE number = ? 
            ORDER BY acct_code, subsidiary_code
        '''
        return self.db.fetch_all(query, (number,))
    
    def get_by_account(self, acct_code: str, start_date: date = None, 
                      end_date: date = None) -> List[Dict]:
        """Get subcode entries for a specific account"""
        query = '''
            SELECT ls.*, l.payee, l.description as ledger_description
            FROM ledger_subcodes ls
            JOIN ledger l ON ls.number = l.number
            WHERE ls.acct_code = ?
        '''
        params = [acct_code]
        
        if start_date:
            query += " AND ls.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND ls.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY ls.date DESC, ls.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_by_subsidiary(self, subsidiary_code: str, start_date: date = None, 
                         end_date: date = None) -> List[Dict]:
        """Get entries for a specific subsidiary code"""
        query = '''
            SELECT ls.*, l.payee, l.description as ledger_description
            FROM ledger_subcodes ls
            JOIN ledger l ON ls.number = l.number
            WHERE ls.subsidiary_code = ?
        '''
        params = [subsidiary_code]
        
        if start_date:
            query += " AND ls.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND ls.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY ls.date DESC, ls.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_by_account_and_subsidiary(self, acct_code: str, subsidiary_code: str,
                                    start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get entries for specific account and subsidiary combination"""
        query = '''
            SELECT ls.*, l.payee, l.description as ledger_description
            FROM ledger_subcodes ls
            JOIN ledger l ON ls.number = l.number
            WHERE ls.acct_code = ? AND ls.subsidiary_code = ?
        '''
        params = [acct_code, subsidiary_code]
        
        if start_date:
            query += " AND ls.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND ls.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY ls.date DESC, ls.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_by_type(self, entry_type: str, start_date: date = None, 
                   end_date: date = None) -> List[Dict]:
        """Get subcode entries by type (VP or CV)"""
        query = '''
            SELECT ls.*, l.payee, l.description as ledger_description
            FROM ledger_subcodes ls
            JOIN ledger l ON ls.number = l.number
            WHERE ls.type = ?
        '''
        params = [entry_type]
        
        if start_date:
            query += " AND ls.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND ls.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY ls.date DESC, ls.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def update(self, entry_id: int, **kwargs) -> bool:
        """Update subcode entry fields"""
        allowed_fields = ['acct_code', 'acct_description', 'subsidiary_code', 
                         'subsidiary_description', 'amount']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE ledger_subcodes 
            SET {set_clause}
            WHERE id = ?
        '''
        
        values = list(updates.values()) + [entry_id]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"Subcode entry {entry_id} updated: {updates}")
        return success
    
    def delete(self, entry_id: int) -> bool:
        """Delete subcode entry"""
        query = 'DELETE FROM ledger_subcodes WHERE id = ?'
        success = self.db.execute_query(query, (entry_id,))
        if success:
            logger.info(f"Subcode entry {entry_id} deleted")
        return success
    
    def delete_by_number(self, number: str) -> bool:
        """Delete all subcode entries for a ledger number"""
        query = 'DELETE FROM ledger_subcodes WHERE number = ?'
        success = self.db.execute_query(query, (number,))
        if success:
            logger.info(f"All subcode entries deleted for ledger {number}")
        return success
    
    def get_subsidiary_totals(self, acct_code: str = None, start_date: date = None, 
                            end_date: date = None) -> List[Dict]:
        """Get totals by subsidiary code"""
        query = '''
            SELECT 
                subsidiary_code,
                subsidiary_description,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount
            FROM ledger_subcodes
            WHERE 1=1
        '''
        params = []
        
        if acct_code:
            query += " AND acct_code = ?"
            params.append(acct_code)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += '''
            GROUP BY subsidiary_code, subsidiary_description
            ORDER BY total_amount DESC
        '''
        
        results = self.db.fetch_all(query, tuple(params))
        
        return [
            {
                'subsidiary_code': row['subsidiary_code'],
                'subsidiary_description': row['subsidiary_description'],
                'transaction_count': row['transaction_count'],
                'total_amount': float(row['total_amount'] or 0)
            }
            for row in results
        ]
    
    def get_account_subsidiary_breakdown(self, acct_code: str, start_date: date = None, 
                                       end_date: date = None) -> List[Dict]:
        """Get subsidiary breakdown for a specific account"""
        return self.get_subsidiary_totals(acct_code, start_date, end_date)
    
    def get_subsidiary_activity(self, subsidiary_code: str, start_date: date = None, 
                              end_date: date = None, limit: int = 100) -> List[Dict]:
        """Get detailed activity for a subsidiary code"""
        query = '''
            SELECT 
                ls.*,
                l.payee,
                l.description as ledger_description,
                l.status
            FROM ledger_subcodes ls
            JOIN ledger l ON ls.number = l.number
            WHERE ls.subsidiary_code = ?
        '''
        params = [subsidiary_code]
        
        if start_date:
            query += " AND ls.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND ls.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY ls.date DESC, ls.number DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        return self.db.fetch_all(query, tuple(params))
    
    def validate_subsidiary_total(self, number: str, acct_code: str) -> Dict:
        """Validate that subsidiary codes sum to the account total"""
        # Get total from main credit/debit entry
        cd_query = '''
            SELECT SUM(amount) as total_amount
            FROM ledger_credit_debit
            WHERE number = ? AND acct_code = ?
        '''
        cd_result = self.db.fetch_one(cd_query, (number, acct_code))
        cd_total = float(cd_result['total_amount'] or 0) if cd_result else 0
        
        # Get total from subsidiary entries
        sub_query = '''
            SELECT SUM(amount) as total_amount
            FROM ledger_subcodes
            WHERE number = ? AND acct_code = ?
        '''
        sub_result = self.db.fetch_one(sub_query, (number, acct_code))
        sub_total = float(sub_result['total_amount'] or 0) if sub_result else 0
        
        difference = abs(cd_total - sub_total)
        
        return {
            'balanced': difference < 0.01,  # Allow for small rounding differences
            'credit_debit_total': cd_total,
            'subsidiary_total': sub_total,
            'difference': difference
        }
    
    def get_subsidiary_codes(self) -> List[Dict]:
        """Get list of all subsidiary codes in use"""
        query = '''
            SELECT DISTINCT subsidiary_code, subsidiary_description
            FROM ledger_subcodes
            ORDER BY subsidiary_code
        '''
        return self.db.fetch_all(query)
    
    def get_monthly_subsidiary_report(self, year: int = None) -> List[Dict]:
        """Get monthly report by subsidiary codes"""
        if year is None:
            year = datetime.now().year
        
        query = '''
            SELECT 
                strftime('%m', date) as month,
                subsidiary_code,
                subsidiary_description,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count
            FROM ledger_subcodes
            WHERE strftime('%Y', date) = ?
            GROUP BY strftime('%m', date), subsidiary_code, subsidiary_description
            ORDER BY month, subsidiary_code
        '''
        
        results = self.db.fetch_all(query, (str(year),))
        
        return [
            {
                'month': row['month'],
                'subsidiary_code': row['subsidiary_code'],
                'subsidiary_description': row['subsidiary_description'],
                'total_amount': float(row['total_amount'] or 0),
                'transaction_count': row['transaction_count']
            }
            for row in results
        ]
    
    def search(self, search_term: str) -> List[Dict]:
        """Search subcode entries by subsidiary code or description"""
        query = '''
            SELECT ls.*, l.payee, l.description as ledger_description
            FROM ledger_subcodes ls
            JOIN ledger l ON ls.number = l.number
            WHERE (ls.subsidiary_code LIKE ? OR ls.subsidiary_description LIKE ? 
                   OR ls.acct_code LIKE ? OR ls.acct_description LIKE ?)
            ORDER BY ls.date DESC
        '''
        
        search_pattern = f'%{search_term}%'
        params = [search_pattern] * 4
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_statistics(self) -> Dict:
        """Get subcode statistics"""
        try:
            stats = {}
            
            # Total entries
            result = self.db.fetch_one('SELECT COUNT(*) as count FROM ledger_subcodes')
            stats['total_entries'] = result['count'] if result else 0
            
            # Unique subsidiary codes
            result = self.db.fetch_one('SELECT COUNT(DISTINCT subsidiary_code) as count FROM ledger_subcodes')
            stats['unique_subsidiary_codes'] = result['count'] if result else 0
            
            # By transaction type
            result = self.db.fetch_all('''
                SELECT type, COUNT(*) as count, SUM(amount) as total_amount
                FROM ledger_subcodes
                GROUP BY type
            ''')
            stats['by_transaction_type'] = {
                row['type']: {
                    'count': row['count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in result
            }
            
            # Top subsidiary codes by activity
            result = self.db.fetch_all('''
                SELECT subsidiary_code, subsidiary_description, 
                       COUNT(*) as transaction_count, SUM(amount) as total_amount
                FROM ledger_subcodes
                GROUP BY subsidiary_code, subsidiary_description
                ORDER BY transaction_count DESC
                LIMIT 10
            ''')
            stats['top_subsidiary_codes'] = [
                {
                    'subsidiary_code': row['subsidiary_code'],
                    'subsidiary_description': row['subsidiary_description'],
                    'transaction_count': row['transaction_count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in result
            ]
            
            # Monthly distribution (last 12 months)
            result = self.db.fetch_all('''
                SELECT 
                    strftime('%Y-%m', date) as month,
                    COUNT(*) as count,
                    SUM(amount) as total_amount
                FROM ledger_subcodes
                WHERE date >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC
            ''')
            stats['monthly_distribution'] = [
                {
                    'month': row['month'],
                    'count': row['count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in result
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting subcode statistics: {e}")
            return {}