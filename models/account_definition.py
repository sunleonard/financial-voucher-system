# models/account_definition.py
"""
Account Definition Model - Chart of Accounts
"""

from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AccountDefinition:
    """Account Definition model for Chart of Accounts"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_table(self) -> bool:
        """Create account definition table"""
        query = '''
            CREATE TABLE IF NOT EXISTS acct_definition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acct_code VARCHAR(50) UNIQUE NOT NULL,
                acct_description VARCHAR(255) NOT NULL,
                acct_type VARCHAR(20) NOT NULL,
                acct_prefix VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        '''
        return self.db.execute_query(query)
    
    def create(self, acct_code: str, acct_description: str, 
               acct_type: str, acct_prefix: str = None) -> Optional[int]:
        """Create a new account definition"""
        query = '''
            INSERT INTO acct_definition (acct_code, acct_description, acct_type, acct_prefix)
            VALUES (?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (acct_code, acct_description, acct_type, acct_prefix))
                account_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Account created: {acct_code} - {acct_description}")
                return account_id
        except Exception as e:
            logger.error(f"Failed to create account {acct_code}: {e}")
            return None
    
    def get_by_code(self, acct_code: str) -> Optional[Dict]:
        """Get account by account code"""
        query = '''
            SELECT id, acct_code, acct_description, acct_type, acct_prefix, 
                   created_at, updated_at, is_active
            FROM acct_definition 
            WHERE acct_code = ? AND is_active = 1
        '''
        return self.db.fetch_one(query, (acct_code,))
    
    def get_by_id(self, account_id: int) -> Optional[Dict]:
        """Get account by ID"""
        query = '''
            SELECT id, acct_code, acct_description, acct_type, acct_prefix, 
                   created_at, updated_at, is_active
            FROM acct_definition 
            WHERE id = ? AND is_active = 1
        '''
        return self.db.fetch_one(query, (account_id,))
    
    def get_all(self, acct_type: str = None, include_inactive: bool = False) -> List[Dict]:
        """Get all accounts, optionally filtered by type"""
        query = '''
            SELECT id, acct_code, acct_description, acct_type, acct_prefix, 
                   created_at, updated_at, is_active
            FROM acct_definition
        '''
        
        params = []
        conditions = []
        
        if not include_inactive:
            conditions.append("is_active = 1")
        
        if acct_type:
            conditions.append("acct_type = ?")
            params.append(acct_type)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY acct_type, acct_code"
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_by_type(self, acct_type: str) -> List[Dict]:
        """Get accounts by type (Company, Customer, Employee, Subsidiary)"""
        query = '''
            SELECT id, acct_code, acct_description, acct_type, acct_prefix, 
                   created_at, updated_at, is_active
            FROM acct_definition 
            WHERE acct_type = ? AND is_active = 1
            ORDER BY acct_code
        '''
        return self.db.fetch_all(query, (acct_type,))
    
    def get_by_prefix(self, acct_prefix: str) -> List[Dict]:
        """Get accounts by prefix"""
        query = '''
            SELECT id, acct_code, acct_description, acct_type, acct_prefix, 
                   created_at, updated_at, is_active
            FROM acct_definition 
            WHERE acct_prefix = ? AND is_active = 1
            ORDER BY acct_code
        '''
        return self.db.fetch_all(query, (acct_prefix,))
    
    def update(self, account_id: int, **kwargs) -> bool:
        """Update account fields"""
        allowed_fields = ['acct_description', 'acct_type', 'acct_prefix', 'is_active']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE acct_definition 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        
        values = list(updates.values()) + [account_id]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"Account {account_id} updated: {updates}")
        return success
    
    def update_by_code(self, acct_code: str, **kwargs) -> bool:
        """Update account by code"""
        allowed_fields = ['acct_description', 'acct_type', 'acct_prefix', 'is_active']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE acct_definition 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE acct_code = ?
        '''
        
        values = list(updates.values()) + [acct_code]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"Account {acct_code} updated: {updates}")
        return success
    
    def soft_delete(self, account_id: int) -> bool:
        """Soft delete account (set inactive)"""
        query = '''
            UPDATE acct_definition 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        success = self.db.execute_query(query, (account_id,))
        if success:
            logger.info(f"Account {account_id} soft deleted")
        return success
    
    def soft_delete_by_code(self, acct_code: str) -> bool:
        """Soft delete account by code"""
        query = '''
            UPDATE acct_definition 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE acct_code = ?
        '''
        success = self.db.execute_query(query, (acct_code,))
        if success:
            logger.info(f"Account {acct_code} soft deleted")
        return success
    
    def search(self, search_term: str, acct_type: str = None) -> List[Dict]:
        """Search accounts by code or description"""
        query = '''
            SELECT id, acct_code, acct_description, acct_type, acct_prefix, 
                   created_at, updated_at, is_active
            FROM acct_definition 
            WHERE (acct_code LIKE ? OR acct_description LIKE ?) AND is_active = 1
        '''
        params = [f'%{search_term}%', f'%{search_term}%']
        
        if acct_type:
            query += ' AND acct_type = ?'
            params.append(acct_type)
        
        query += ' ORDER BY acct_code'
        
        return self.db.fetch_all(query, tuple(params))
    
    def is_code_available(self, acct_code: str, exclude_id: int = None) -> bool:
        """Check if account code is available"""
        query = 'SELECT id FROM acct_definition WHERE acct_code = ?'
        params = [acct_code]
        
        if exclude_id:
            query += ' AND id != ?'
            params.append(exclude_id)
        
        result = self.db.fetch_one(query, tuple(params))
        return result is None
    
    def get_account_types(self) -> List[str]:
        """Get list of distinct account types"""
        query = '''
            SELECT DISTINCT acct_type 
            FROM acct_definition 
            WHERE is_active = 1 
            ORDER BY acct_type
        '''
        results = self.db.fetch_all(query)
        return [row['acct_type'] for row in results]
    
    def get_account_prefixes(self) -> List[str]:
        """Get list of distinct account prefixes"""
        query = '''
            SELECT DISTINCT acct_prefix 
            FROM acct_definition 
            WHERE is_active = 1 AND acct_prefix IS NOT NULL 
            ORDER BY acct_prefix
        '''
        results = self.db.fetch_all(query)
        return [row['acct_prefix'] for row in results]
    
    def get_accounts_by_category(self) -> Dict[str, List[Dict]]:
        """Get accounts grouped by type"""
        accounts = self.get_all()
        
        categories = {}
        for account in accounts:
            acct_type = account['acct_type']
            if acct_type not in categories:
                categories[acct_type] = []
            categories[acct_type].append(account)
        
        return categories
    
    def get_account_statistics(self) -> Dict:
        """Get account statistics"""
        try:
            stats = {}
            
            # Total accounts
            result = self.db.fetch_one('SELECT COUNT(*) as count FROM acct_definition WHERE is_active = 1')
            stats['total_accounts'] = result['count'] if result else 0
            
            # Accounts by type
            result = self.db.fetch_all('''
                SELECT acct_type, COUNT(*) as count 
                FROM acct_definition 
                WHERE is_active = 1 
                GROUP BY acct_type
            ''')
            stats['by_type'] = {row['acct_type']: row['count'] for row in result}
            
            # Accounts by prefix
            result = self.db.fetch_all('''
                SELECT acct_prefix, COUNT(*) as count 
                FROM acct_definition 
                WHERE is_active = 1 AND acct_prefix IS NOT NULL
                GROUP BY acct_prefix
            ''')
            stats['by_prefix'] = {row['acct_prefix']: row['count'] for row in result}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting account statistics: {e}")
            return {}
    
    def validate_account_code(self, acct_code: str) -> tuple[bool, str]:
        """Validate account code format and uniqueness"""
        if not acct_code:
            return False, "Account code is required"
        
        if len(acct_code) > 50:
            return False, "Account code too long (max 50 characters)"
        
        # Check if code already exists
        if not self.is_code_available(acct_code):
            return False, "Account code already exists"
        
        return True, "Valid"
    
    def get_payees(self) -> List[Dict]:
        """Get accounts that can be used as payees (Companies, Customers, Employees)"""
        query = '''
            SELECT acct_code, acct_description, acct_type, acct_prefix
            FROM acct_definition 
            WHERE acct_type IN ('Company', 'Customer', 'Employee') 
            AND is_active = 1
            ORDER BY acct_description
        '''
        return self.db.fetch_all(query)