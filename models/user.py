# models/user.py
"""
User Model - Handles user data structure and basic operations
"""

from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class User:
    """User model class"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_table(self) -> bool:
        """Create users table"""
        query = '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(64) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                company_id VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (company_id)
            )
        '''
        return self.db.execute_query(query)
    
    def create(self, username: str, email: str, password_hash: str, 
               salt: str, role: str = 'user', company_id: str = None) -> Optional[int]:
        """Create a new user"""
        query = '''
            INSERT INTO users (username, email, password_hash, salt, role, company_id)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (username, email, password_hash, salt, role, company_id))
                user_id = cursor.lastrowid
                conn.commit()
                logger.info(f"User created: {username} (ID: {user_id})")
                return user_id
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None
    
    def get_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        query = '''
            SELECT id, username, email, role, company_id, created_at, 
                   updated_at, last_login, is_active, failed_login_attempts
            FROM users 
            WHERE id = ? AND is_active = 1
        '''
        return self.db.fetch_one(query, (user_id,))
    
    def get_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username (for authentication)"""
        query = '''
            SELECT id, username, email, password_hash, salt, role, company_id, 
                   is_active, failed_login_attempts, locked_until
            FROM users 
            WHERE username = ?
        '''
        return self.db.fetch_one(query, (username,))
    
    def get_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        query = '''
            SELECT id, username, email, role, company_id, created_at, 
                   updated_at, is_active
            FROM users 
            WHERE email = ?
        '''
        return self.db.fetch_one(query, (email,))
    
    def get_all(self, include_inactive: bool = False) -> List[Dict]:
        """Get all users"""
        query = '''
            SELECT u.id, u.username, u.email, u.role, u.company_id, 
                   u.created_at, u.updated_at, u.last_login, u.is_active,
                   c.company_name
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.company_id
        '''
        
        if not include_inactive:
            query += ' WHERE u.is_active = 1'
        
        query += ' ORDER BY u.created_at DESC'
        
        return self.db.fetch_all(query)
    
    def get_by_company(self, company_id: str) -> List[Dict]:
        """Get users by company"""
        query = '''
            SELECT id, username, email, role, created_at, updated_at, 
                   last_login, is_active
            FROM users 
            WHERE company_id = ? AND is_active = 1
            ORDER BY username
        '''
        return self.db.fetch_all(query, (company_id,))
    
    def update(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        allowed_fields = ['username', 'email', 'role', 'company_id', 'is_active']
        
        # Filter only allowed fields
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        # Build dynamic query
        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
        query = f'''
            UPDATE users 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        
        values = list(updates.values()) + [user_id]
        
        success = self.db.execute_query(query, tuple(values))
        if success:
            logger.info(f"User {user_id} updated: {updates}")
        return success
    
    def update_password(self, user_id: int, password_hash: str, salt: str) -> bool:
        """Update user password"""
        query = '''
            UPDATE users 
            SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        success = self.db.execute_query(query, (password_hash, salt, user_id))
        if success:
            logger.info(f"Password updated for user {user_id}")
        return success
    
    def update_last_login(self, user_id: int) -> bool:
        """Update last login timestamp"""
        query = '''
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP, failed_login_attempts = 0, locked_until = NULL
            WHERE id = ?
        '''
        return self.db.execute_query(query, (user_id,))
    
    def increment_failed_attempts(self, user_id: int) -> bool:
        """Increment failed login attempts"""
        query = '''
            UPDATE users 
            SET failed_login_attempts = failed_login_attempts + 1,
                locked_until = CASE 
                    WHEN failed_login_attempts >= 4 THEN datetime('now', '+30 minutes')
                    ELSE locked_until 
                END
            WHERE id = ?
        '''
        return self.db.execute_query(query, (user_id,))
    
    def soft_delete(self, user_id: int) -> bool:
        """Soft delete user (set inactive)"""
        query = '''
            UPDATE users 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        success = self.db.execute_query(query, (user_id,))
        if success:
            logger.info(f"User {user_id} soft deleted")
        return success
    
    def hard_delete(self, user_id: int) -> bool:
        """Hard delete user (permanent removal)"""
        query = 'DELETE FROM users WHERE id = ?'
        success = self.db.execute_query(query, (user_id,))
        if success:
            logger.warning(f"User {user_id} permanently deleted")
        return success
    
    def search(self, search_term: str, role: str = None, company_id: str = None) -> List[Dict]:
        """Search users by username or email"""
        query = '''
            SELECT u.id, u.username, u.email, u.role, u.company_id, 
                   u.created_at, u.is_active, c.company_name
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.company_id
            WHERE (u.username LIKE ? OR u.email LIKE ?)
        '''
        params = [f'%{search_term}%', f'%{search_term}%']
        
        if role:
            query += ' AND u.role = ?'
            params.append(role)
        
        if company_id:
            query += ' AND u.company_id = ?'
            params.append(company_id)
        
        query += ' ORDER BY u.username'
        
        return self.db.fetch_all(query, tuple(params))
    
    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        stats = {}
        
        # Total users
        result = self.db.fetch_one('SELECT COUNT(*) as total FROM users WHERE is_active = 1')
        stats['total_users'] = result['total'] if result else 0
        
        # Users by role
        result = self.db.fetch_all('''
            SELECT role, COUNT(*) as count 
            FROM users 
            WHERE is_active = 1 
            GROUP BY role
        ''')
        stats['by_role'] = {row['role']: row['count'] for row in result}
        
        # Recent logins (last 7 days)
        result = self.db.fetch_one('''
            SELECT COUNT(*) as count 
            FROM users 
            WHERE last_login >= datetime('now', '-7 days') AND is_active = 1
        ''')
        stats['recent_logins'] = result['count'] if result else 0
        
        # Locked accounts
        result = self.db.fetch_one('''
            SELECT COUNT(*) as count 
            FROM users 
            WHERE locked_until > datetime('now') AND is_active = 1
        ''')
        stats['locked_accounts'] = result['count'] if result else 0
        
        return stats
    
    def is_username_available(self, username: str, exclude_user_id: int = None) -> bool:
        """Check if username is available"""
        query = 'SELECT id FROM users WHERE username = ?'
        params = [username]
        
        if exclude_user_id:
            query += ' AND id != ?'
            params.append(exclude_user_id)
        
        result = self.db.fetch_one(query, tuple(params))
        return result is None
    
    def is_email_available(self, email: str, exclude_user_id: int = None) -> bool:
        """Check if email is available"""
        query = 'SELECT id FROM users WHERE email = ?'
        params = [email]
        
        if exclude_user_id:
            query += ' AND id != ?'
            params.append(exclude_user_id)
        
        result = self.db.fetch_one(query, tuple(params))
        return result is None