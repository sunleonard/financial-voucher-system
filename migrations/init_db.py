# migrations/init_db.py
"""
Database Initialization - Create all tables and default data
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

def create_schema(db_path: str) -> bool:
    """Create all database tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
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
        ''')
        
        # Companies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id VARCHAR(20) UNIQUE NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                business_type VARCHAR(10) DEFAULT 'B2B',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # System logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action VARCHAR(100) NOT NULL,
                table_name VARCHAR(50),
                record_id VARCHAR(50),
                old_values TEXT,
                new_values TEXT,
                ip_address VARCHAR(45),
                user_agent TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Vouchers Payable table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vouchers_payable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vp_number VARCHAR(50) UNIQUE NOT NULL,
                company_id VARCHAR(20) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                amount_to_pay DECIMAL(15,2) NOT NULL,
                account_code VARCHAR(20) NOT NULL,
                subcode VARCHAR(10) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date DATE,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (company_id) REFERENCES companies (company_id)
            )
        ''')
        
        # Check Vouchers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS check_vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cv_number VARCHAR(50) UNIQUE NOT NULL,
                vp_number VARCHAR(50),
                company_id VARCHAR(20) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                amount_to_pay DECIMAL(15,2) NOT NULL,
                account_code VARCHAR(20) NOT NULL,
                subcode VARCHAR(10) NOT NULL,
                check_number VARCHAR(50),
                bank_account VARCHAR(50),
                description TEXT,
                status VARCHAR(20) DEFAULT 'issued',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                check_date DATE,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (vp_number) REFERENCES vouchers_payable (vp_number)
            )
        ''')
        
        # Bank Memos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memo_number VARCHAR(50) UNIQUE NOT NULL,
                bank_account VARCHAR(50) NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                description TEXT,
                reference_number VARCHAR(50),
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_date DATE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Purchase Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number VARCHAR(50) UNIQUE NOT NULL,
                supplier_id VARCHAR(20) NOT NULL,
                supplier_name VARCHAR(255) NOT NULL,
                total_amount DECIMAL(15,2) NOT NULL,
                account_code VARCHAR(20) NOT NULL,
                subcode VARCHAR(10) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivery_date DATE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Account Codes reference table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_code VARCHAR(20) UNIQUE NOT NULL,
                business_type VARCHAR(10) NOT NULL,
                description VARCHAR(255),
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Subcodes reference table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subcodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subcode VARCHAR(10) UNIQUE NOT NULL,
                description VARCHAR(255),
                transaction_type VARCHAR(50),
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create indexes for better performance
        create_indexes(db_path)
        
        logger.info("Database schema created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating database schema: {e}")
        return False

def create_indexes(db_path: str) -> bool:
    """Create database indexes for better performance"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        indexes = [
            # Users table indexes
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)",
            
            # Companies table indexes
            "CREATE INDEX IF NOT EXISTS idx_companies_company_id ON companies(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_companies_is_active ON companies(is_active)",
            
            # System logs indexes
            "CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_action ON system_logs(action)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_table_name ON system_logs(table_name)",
            
            # Vouchers indexes
            "CREATE INDEX IF NOT EXISTS idx_vouchers_payable_company_id ON vouchers_payable(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_payable_status ON vouchers_payable(status)",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_payable_created_by ON vouchers_payable(created_by)",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_payable_created_at ON vouchers_payable(created_at)",
            
            # Check vouchers indexes
            "CREATE INDEX IF NOT EXISTS idx_check_vouchers_vp_number ON check_vouchers(vp_number)",
            "CREATE INDEX IF NOT EXISTS idx_check_vouchers_company_id ON check_vouchers(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_check_vouchers_created_by ON check_vouchers(created_by)",
            
            # Purchase orders indexes
            "CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id ON purchase_orders(supplier_id)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON purchase_orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_orders_created_by ON purchase_orders(created_by)"
        ]
        
        for index_query in indexes:
            cursor.execute(index_query)
        
        conn.commit()
        conn.close()
        
        logger.info("Database indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        return False

def insert_default_data(db_path: str) -> bool:
    """Insert default reference data"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Default account codes
        account_codes = [
            ('201', 'B2B', 'Business to Business transactions'),
            ('101', 'B2C', 'Business to Consumer transactions')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO account_codes (account_code, business_type, description)
            VALUES (?, ?, ?)
        ''', account_codes)
        
        # Default subcodes
        subcodes = [
            ('-10', 'General Expenses', 'Regular operational expenses'),
            ('-11', 'Office Supplies', 'Office and administrative supplies'),
            ('-20', 'Utilities', 'Utility payments and services'),
            ('-21', 'Professional Services', 'Consulting and professional fees'),
            ('-30', 'Travel', 'Business travel expenses'),
            ('-31', 'Meals & Entertainment', 'Business meals and entertainment'),
            ('-40', 'Equipment', 'Equipment purchases and leases'),
            ('-41', 'Software', 'Software licenses and subscriptions'),
            ('-50', 'Marketing', 'Marketing and advertising expenses'),
            ('-60', 'Insurance', 'Insurance premiums and claims')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO subcodes (subcode, description, transaction_type)
            VALUES (?, ?, ?)
        ''', subcodes)
        
        conn.commit()
        conn.close()
        
        logger.info("Default reference data inserted successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error inserting default data: {e}")
        return False

def reset_database(db_path: str) -> bool:
    """Reset the entire database (USE WITH CAUTION!)"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # Drop all tables
        for table in tables:
            if table[0] != 'sqlite_sequence':  # Don't drop SQLite system table
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
        
        conn.commit()
        conn.close()
        
        # Recreate schema and data
        create_schema(db_path)
        insert_default_data(db_path)
        
        logger.warning("Database reset completed")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

def get_database_info(db_path: str) -> dict:
    """Get information about the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        info = {}
        
        # Get table information
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = cursor.fetchall()
        info['tables'] = {}
        
        for table_name, create_sql in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            info['tables'][table_name] = {
                'row_count': row_count,
                'columns': len(columns),
                'column_details': [
                    {
                        'name': col[1],
                        'type': col[2],
                        'not_null': bool(col[3]),
                        'primary_key': bool(col[5])
                    }
                    for col in columns
                ]
            }
        
        # Get database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()[0]
        info['database_size_bytes'] = db_size
        info['database_size_mb'] = round(db_size / (1024 * 1024), 2)
        
        conn.close()
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {}

if __name__ == "__main__":
    # Test database creation
    import os
    
    test_db = "test_financial_system.db"
    
    print("Creating test database...")
    success = create_schema(test_db)
    if success:
        print("✅ Schema created successfully")
        
        success = insert_default_data(test_db)
        if success:
            print("✅ Default data inserted successfully")
            
            info = get_database_info(test_db)
            print(f"✅ Database created with {len(info['tables'])} tables")
            
            # Cleanup
            os.remove(test_db)
            print("✅ Test database cleaned up")
        else:
            print("❌ Failed to insert default data")
    else:
        print("❌ Failed to create schema")