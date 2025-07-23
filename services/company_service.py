# services/company_service.py
"""
Company Service - Business logic for company management
"""

from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class CompanyService:
    """Company management service"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_company_table(self) -> bool:
        """Create companies table"""
        query = '''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id VARCHAR(20) UNIQUE NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                business_type VARCHAR(10) DEFAULT 'B2B',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        '''
        return self.db.execute_query(query)
    
    def create_company(self, company_id: str, company_name: str, 
                      business_type: str = 'B2B', created_by: int = None) -> Tuple[bool, str]:
        """
        Create a new company
        Returns: (success, message)
        """
        try:
            # Validate input
            if not company_id or not company_name:
                return False, "Company ID and name are required"
            
            if business_type not in ['B2B', 'B2C']:
                return False, "Business type must be B2B or B2C"
            
            # Check if company ID already exists
            existing = self.get_company_by_id(company_id)
            if existing:
                return False, "Company ID already exists"
            
            # Create company
            query = '''
                INSERT INTO companies (company_id, company_name, business_type)
                VALUES (?, ?, ?)
            '''
            
            success = self.db.execute_query(query, (company_id, company_name, business_type))
            
            if success:
                logger.info(f"Company created: {company_id} - {company_name}")
                return True, "Company created successfully"
            else:
                return False, "Failed to create company"
                
        except Exception as e:
            logger.error(f"Error creating company: {e}")
            return False, "An error occurred while creating the company"
    
    def get_company_by_id(self, company_id: str) -> Optional[Dict]:
        """Get company by company_id"""
        query = '''
            SELECT company_id, company_name, business_type, created_at, updated_at, is_active
            FROM companies 
            WHERE company_id = ? AND is_active = 1
        '''
        return self.db.fetch_one(query, (company_id,))
    
    def get_all_companies(self, include_inactive: bool = False) -> List[Dict]:
        """Get all companies"""
        query = '''
            SELECT company_id, company_name, business_type, created_at, updated_at, is_active
            FROM companies
        '''
        
        if not include_inactive:
            query += ' WHERE is_active = 1'
        
        query += ' ORDER BY company_name'
        
        return self.db.fetch_all(query)
    
    def update_company(self, company_id: str, company_name: str = None,
                      business_type: str = None, updated_by: int = None) -> Tuple[bool, str]:
        """
        Update company information
        Returns: (success, message)
        """
        try:
            # Check if company exists
            existing = self.get_company_by_id(company_id)
            if not existing:
                return False, "Company not found"
            
            # Build update query
            updates = []
            params = []
            
            if company_name is not None:
                updates.append("company_name = ?")
                params.append(company_name)
            
            if business_type is not None:
                if business_type not in ['B2B', 'B2C']:
                    return False, "Business type must be B2B or B2C"
                updates.append("business_type = ?")
                params.append(business_type)
            
            if not updates:
                return False, "No updates provided"
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(company_id)
            
            query = f"UPDATE companies SET {', '.join(updates)} WHERE company_id = ?"
            
            success = self.db.execute_query(query, tuple(params))
            
            if success:
                logger.info(f"Company updated: {company_id}")
                return True, "Company updated successfully"
            else:
                return False, "Failed to update company"
                
        except Exception as e:
            logger.error(f"Error updating company: {e}")
            return False, "An error occurred while updating the company"
    
    def delete_company(self, company_id: str, deleted_by: int = None) -> Tuple[bool, str]:
        """
        Soft delete company
        Returns: (success, message)
        """
        try:
            # Check if company exists
            existing = self.get_company_by_id(company_id)
            if not existing:
                return False, "Company not found"
            
            # Check if company has associated users
            users_count = self.db.fetch_one('''
                SELECT COUNT(*) as count 
                FROM users 
                WHERE company_id = ? AND is_active = 1
            ''', (company_id,))
            
            if users_count and users_count['count'] > 0:
                return False, f"Cannot delete company with {users_count['count']} active users"
            
            # Soft delete
            query = '''
                UPDATE companies 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                WHERE company_id = ?
            '''
            
            success = self.db.execute_query(query, (company_id,))
            
            if success:
                logger.info(f"Company deleted: {company_id}")
                return True, "Company deleted successfully"
            else:
                return False, "Failed to delete company"
                
        except Exception as e:
            logger.error(f"Error deleting company: {e}")
            return False, "An error occurred while deleting the company"
    
    def search_companies(self, search_term: str) -> List[Dict]:
        """Search companies by name or ID"""
        query = '''
            SELECT company_id, company_name, business_type, created_at, is_active
            FROM companies 
            WHERE (company_name LIKE ? OR company_id LIKE ?) AND is_active = 1
            ORDER BY company_name
        '''
        
        search_pattern = f'%{search_term}%'
        return self.db.fetch_all(query, (search_pattern, search_pattern))
    
    def get_company_statistics(self) -> Dict:
        """Get company statistics"""
        try:
            stats = {}
            
            # Total companies
            result = self.db.fetch_one('SELECT COUNT(*) as count FROM companies WHERE is_active = 1')
            stats['total_companies'] = result['count'] if result else 0
            
            # Companies by type
            result = self.db.fetch_all('''
                SELECT business_type, COUNT(*) as count 
                FROM companies 
                WHERE is_active = 1 
                GROUP BY business_type
            ''')
            stats['by_type'] = {row['business_type']: row['count'] for row in result}
            
            # Companies with users
            result = self.db.fetch_one('''
                SELECT COUNT(DISTINCT c.company_id) as count
                FROM companies c
                INNER JOIN users u ON c.company_id = u.company_id
                WHERE c.is_active = 1 AND u.is_active = 1
            ''')
            stats['with_users'] = result['count'] if result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting company statistics: {e}")
            return {}
    
    def insert_default_companies(self) -> bool:
        """Insert some default companies for testing"""
        try:
            default_companies = [
                ('UMT01', 'Universal Manufacturing Ltd', 'B2B'),
                ('RTC02', 'Retail Tech Corp', 'B2C'),
                ('SRV03', 'Service Solutions Inc', 'B2B'),
                ('LOG04', 'Logistics Express Co', 'B2B'),
                ('CON05', 'Consumer Goods Inc', 'B2C')
            ]
            
            for company_id, company_name, business_type in default_companies:
                # Check if already exists
                existing = self.get_company_by_id(company_id)
                if not existing:
                    self.create_company(company_id, company_name, business_type)
            
            logger.info("Default companies inserted")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting default companies: {e}")
            return False