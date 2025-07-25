# models/ledger.py
"""
Ledger Model - Main Transaction Headers (VP/CV)
"""

from typing import Optional, Dict, List
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class Ledger:
    """Ledger model for main transaction headers"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_table(self) -> bool:
        """Create ledger table"""
        query = '''
            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR(10) NOT NULL,
                number VARCHAR(50) UNIQUE NOT NULL,
                date DATE NOT NULL,
                payee_code VARCHAR(50) NOT NULL,
                payee VARCHAR(255) NOT NULL,
                total_amount DECIMAL(15,2) NOT NULL,
                description TEXT,
                due_date DATE,
                status VARCHAR(20) DEFAULT 'active',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (payee_code) REFERENCES acct_definition (acct_code)
            )
        '''
        return self.db.execute_query(query)
    
    def generate_number(self, ledger_type: str, year: int = None) -> str:
        """Generate next ledger number in format: 1-001-2015"""
        if year is None:
            year = datetime.now().year
        
        try:
            # Get the highest number for this type and year
            query = '''
                SELECT number FROM ledger 
                WHERE type = ? AND number LIKE ? 
                ORDER BY CAST(SUBSTR(number, INSTR(number, '-') + 1, 
                               INSTR(SUBSTR(number, INSTR(number, '-') + 1), '-') - 1) AS INTEGER) DESC 
                LIMIT 1
            '''
            
            result = self.db.fetch_one(query, (ledger_type, f'%-{year}'))
            
            if result:
                # Extract sequence number and increment
                parts = result['number'].split('-')
                if len(parts) == 3:
                    sequence = int(parts[1]) + 1
                else:
                    sequence = 1
            else:
                sequence = 1
            
            # Format: 1-001-2015
            return f"1-{sequence:03d}-{year}"
            
        except Exception as e:
            logger.error(f"Error generating ledger number: {e}")
            return f"1-001-{year}"
    
    def create(self, ledger_type: str, transaction_date: date, payee_code: str, 
               payee: str, total_amount: float, description: str = None, 
               due_date: date = None, created_by: int = None, 
               number: str = None) -> Optional[int]:
        """Create a new ledger entry"""
        
        # Generate number if not provided
        if not number:
            number = self.generate_number(ledger_type, transaction_date.year)
        
        query = '''
            INSERT INTO ledger (type, number, date, payee_code, payee, total_amount, 
                              description, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    ledger_type, number, transaction_date, payee_code, payee, 
                    total_amount, description, due_date, created_by
                ))
                ledger_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Ledger entry created: {number} - {payee} - ${total_amount}")
                return ledger_id
        except Exception as e:
            logger.error(f"Failed to create ledger entry {number}: {e}")
            return None
    
    def get_by_id(self, ledger_id: int) -> Optional[Dict]:
        """Get ledger entry by ID"""
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.id = ?
        '''
        return self.db.fetch_one(query, (ledger_id,))
    
    def get_by_number(self, number: str) -> Optional[Dict]:
        """Get ledger entry by number"""
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.number = ?
        '''
        return self.db.fetch_one(query, (number,))
    
    def get_all(self, ledger_type: str = None, status: str = None, 
                start_date: date = None, end_date: date = None,
                limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get ledger entries with optional filters"""
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE 1=1
        '''
        
        params = []
        
        if ledger_type:
            query += " AND l.type = ?"
            params.append(ledger_type)
        
        if status:
            query += " AND l.status = ?"
            params.append(status)
        
        if start_date:
            query += " AND l.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND l.date <= ?"
            params.append(end_date)
        
        query += " ORDER BY l.date DESC, l.number DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_by_payee(self, payee_code: str) -> List[Dict]:
        """Get ledger entries by payee"""
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.payee_code = ?
            ORDER BY l.date DESC
        '''
        return self.db.fetch_all(query, (payee_code,))
    
    def get_by_date_range(self, start_date: date, end_date: date, 
                         ledger_type: str = None) -> List[Dict]:
        """Get ledger entries by date range"""
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.date BETWEEN ? AND ?
        '''
        params = [start_date, end_date]
        
        if ledger_type:
            query += " AND l.type = ?"
            params.append(ledger_type)
        
        query += " ORDER BY l.date DESC, l.number DESC"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_overdue(self, as_of_date: date = None) -> List[Dict]:
        """Get overdue ledger entries"""
        if as_of_date is None:
            as_of_date = date.today()
        
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.due_date < ? AND l.status = 'active'
            ORDER BY l.due_date ASC
        '''
        return self.db.fetch_all(query, (as_of_date,))
    
    def update(self, ledger_id: int, **kwargs) -> bool:
        """Update ledger entry fields"""
        allowed_fields = ['payee_code', 'payee', 'total_amount', 'description', 
                         'due_date', 'status']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE ledger 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        
        values = list(updates.values()) + [ledger_id]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"Ledger entry {ledger_id} updated: {updates}")
        return success
    
    def update_by_number(self, number: str, **kwargs) -> bool:
        """Update ledger entry by number"""
        allowed_fields = ['payee_code', 'payee', 'total_amount', 'description', 
                         'due_date', 'status']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE ledger 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE number = ?
        '''
        
        values = list(updates.values()) + [number]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"Ledger entry {number} updated: {updates}")
        return success
    
    def delete(self, ledger_id: int) -> bool:
        """Delete ledger entry (hard delete - use with caution)"""
        # First delete related records
        number_result = self.db.fetch_one("SELECT number FROM ledger WHERE id = ?", (ledger_id,))
        if number_result:
            number = number_result['number']
            
            # Delete related credit/debit entries
            self.db.execute_query("DELETE FROM ledger_credit_debit WHERE number = ?", (number,))
            
            # Delete related subcode entries  
            self.db.execute_query("DELETE FROM ledger_subcodes WHERE number = ?", (number,))
        
        # Delete main ledger entry
        query = 'DELETE FROM ledger WHERE id = ?'
        success = self.db.execute_query(query, (ledger_id,))
        if success:
            logger.warning(f"Ledger entry {ledger_id} permanently deleted")
        return success
    
    def void(self, ledger_id: int) -> bool:
        """Void ledger entry (change status to void)"""
        query = '''
            UPDATE ledger 
            SET status = 'void', updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        success = self.db.execute_query(query, (ledger_id,))
        if success:
            logger.info(f"Ledger entry {ledger_id} voided")
        return success
    
    def search(self, search_term: str, ledger_type: str = None) -> List[Dict]:
        """Search ledger entries by number, payee, or description"""
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE (l.number LIKE ? OR l.payee LIKE ? OR l.description LIKE ?)
        '''
        params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']
        
        if ledger_type:
            query += ' AND l.type = ?'
            params.append(ledger_type)
        
        query += ' ORDER BY l.date DESC'
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_statistics(self, ledger_type: str = None, year: int = None) -> Dict:
        """Get ledger statistics"""
        try:
            stats = {}
            
            # Base conditions
            conditions = []
            params = []
            
            if ledger_type:
                conditions.append("type = ?")
                params.append(ledger_type)
            
            if year:
                conditions.append("strftime('%Y', date) = ?")
                params.append(str(year))
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            # Total count and amount
            query = f'''
                SELECT 
                    COUNT(*) as total_count,
                    SUM(total_amount) as total_amount,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
                    SUM(CASE WHEN status = 'active' THEN total_amount ELSE 0 END) as active_amount,
                    COUNT(CASE WHEN due_date < date('now') AND status = 'active' THEN 1 END) as overdue_count,
                    SUM(CASE WHEN due_date < date('now') AND status = 'active' THEN total_amount ELSE 0 END) as overdue_amount
                FROM ledger
                {where_clause}
            '''
            
            result = self.db.fetch_one(query, tuple(params))
            if result:
                stats.update({
                    'total_count': result['total_count'] or 0,
                    'total_amount': float(result['total_amount'] or 0),
                    'active_count': result['active_count'] or 0,
                    'active_amount': float(result['active_amount'] or 0),
                    'overdue_count': result['overdue_count'] or 0,
                    'overdue_amount': float(result['overdue_amount'] or 0)
                })
            
            # By type (if not filtered)
            if not ledger_type:
                query = '''
                    SELECT type, COUNT(*) as count, SUM(total_amount) as amount
                    FROM ledger
                    GROUP BY type
                '''
                if year:
                    query = '''
                        SELECT type, COUNT(*) as count, SUM(total_amount) as amount
                        FROM ledger
                        WHERE strftime('%Y', date) = ?
                        GROUP BY type
                    '''
                    type_results = self.db.fetch_all(query, (str(year),))
                else:
                    type_results = self.db.fetch_all(query)
                
                stats['by_type'] = {
                    row['type']: {
                        'count': row['count'],
                        'amount': float(row['amount'] or 0)
                    }
                    for row in type_results
                }
            
            # Monthly breakdown
            monthly_query = f'''
                SELECT 
                    strftime('%Y-%m', date) as month,
                    COUNT(*) as count,
                    SUM(total_amount) as amount
                FROM ledger
                {where_clause}
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC
                LIMIT 12
            '''
            
            monthly_results = self.db.fetch_all(monthly_query, tuple(params))
            stats['monthly'] = [
                {
                    'month': row['month'],
                    'count': row['count'],
                    'amount': float(row['amount'] or 0)
                }
                for row in monthly_results
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting ledger statistics: {e}")
            return {}
    
    def is_number_available(self, number: str, exclude_id: int = None) -> bool:
        """Check if ledger number is available"""
        query = 'SELECT id FROM ledger WHERE number = ?'
        params = [number]
        
        if exclude_id:
            query += ' AND id != ?'
            params.append(exclude_id)
        
        result = self.db.fetch_one(query, tuple(params))
        return result is None
    
    def get_next_due(self, days: int = 30) -> List[Dict]:
        """Get entries due within specified days"""
        future_date = date.today().replace(day=date.today().day + days) if days <= 31 else None
        
        query = '''
            SELECT l.*, u.username as created_by_username
            FROM ledger l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.due_date BETWEEN date('now') AND date('now', '+{} days')
            AND l.status = 'active'
            ORDER BY l.due_date ASC
        '''.format(days)
        
        return self.db.fetch_all(query)
    
    def get_total_by_payee(self, start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get total amounts by payee"""
        query = '''
            SELECT 
                payee_code,
                payee,
                COUNT(*) as transaction_count,
                SUM(total_amount) as total_amount
            FROM ledger
            WHERE status = 'active'
        '''
        
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += '''
            GROUP BY payee_code, payee
            ORDER BY total_amount DESC
        '''
        
        return self.db.fetch_all(query, tuple(params))