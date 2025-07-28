# migrations/migrate_to_ledger.py
"""
Migration script to upgrade from old voucher structure to new accounting ledger structure
"""

import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

def backup_database(db_path: str) -> str:
    """Create backup of existing database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    return ""

def migrate_to_ledger_structure(db_path: str) -> bool:
    """Migrate from old voucher structure to new accounting ledger"""
    try:
        # Create backup first
        backup_path = backup_database(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Migrating to new accounting ledger structure...")
        
        # 1. Create new accounting tables
        print("📝 Creating new accounting tables...")
        
        # Account Definitions (Chart of Accounts)
        cursor.execute('''
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
        ''')
        
        # Main Ledger (Transaction Headers)
        cursor.execute('''
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
        ''')
        
        # Ledger Credit/Debit (Double-entry lines)
        cursor.execute('''
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
        ''')
        
        # Ledger Subcodes (Subsidiary breakdown)
        cursor.execute('''
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
        ''')
        
        # 2. Create indexes
        print("📇 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_acct_definition_code ON acct_definition(acct_code)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_number ON ledger(number)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_type ON ledger(type)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger(date)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_cd_number ON ledger_credit_debit(number)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_sub_number ON ledger_subcodes(number)"
        ]
        
        for index_query in indexes:
            cursor.execute(index_query)
        
        # 3. Insert default account definitions
        print("💼 Inserting default chart of accounts...")
        default_accounts = [
            # Company Accounts
            ('1000', 'Petty Cash', 'Company', 'CASH'),
            ('1010', 'Bank - Operating Account', 'Company', 'BANK'),
            ('1020', 'Bank - Savings Account', 'Company', 'BANK'),
            ('1100', 'Accounts Receivable', 'Company', 'AR'),
            ('1200', 'Inventory', 'Company', 'INV'),
            ('1300', 'Office Equipment', 'Company', 'EQUIP'),
            ('1400', 'Accumulated Depreciation', 'Company', 'ACCUM'),
            
            # Liability Accounts
            ('2000', 'Accounts Payable', 'Company', 'AP'),
            ('2100', 'Accrued Expenses', 'Company', 'ACCR'),
            ('2200', 'Notes Payable', 'Company', 'NOTES'),
            
            # Equity Accounts
            ('3000', 'Owner\'s Equity', 'Company', 'EQUITY'),
            ('3100', 'Retained Earnings', 'Company', 'RE'),
            
            # Revenue Accounts
            ('4000', 'Sales Revenue', 'Company', 'REV'),
            ('4100', 'Service Revenue', 'Company', 'REV'),
            ('4200', 'Interest Income', 'Company', 'REV'),
            
            # Expense Accounts
            ('5000', 'Office Supplies', 'Company', 'EXP'),
            ('5010', 'Utilities', 'Company', 'EXP'),
            ('5020', 'Rent Expense', 'Company', 'EXP'),
            ('5030', 'Insurance Expense', 'Company', 'EXP'),
            ('5040', 'Professional Services', 'Company', 'EXP'),
            ('5050', 'Travel Expense', 'Company', 'EXP'),
            ('5060', 'Meals & Entertainment', 'Company', 'EXP'),
            ('5070', 'Equipment Rental', 'Company', 'EXP'),
            ('5080', 'Software & Licenses', 'Company', 'EXP'),
            ('5090', 'Marketing & Advertising', 'Company', 'EXP'),
            
            # Sample Customers
            ('CUST001', 'ABC Corporation', 'Customer', 'CUST'),
            ('CUST002', 'XYZ Industries', 'Customer', 'CUST'),
            ('CUST003', 'Global Tech Solutions', 'Customer', 'CUST'),
            
            # Sample Suppliers/Vendors
            ('VEND001', 'Office Supply Co.', 'Company', 'VEND'),
            ('VEND002', 'Tech Equipment Inc.', 'Company', 'VEND'),
            ('VEND003', 'Professional Services LLC', 'Company', 'VEND'),
            ('VEND004', 'Utility Company', 'Company', 'VEND'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO acct_definition (acct_code, acct_description, acct_type, acct_prefix)
            VALUES (?, ?, ?, ?)
        ''', default_accounts)
        
        # 4. Migrate existing voucher data if tables exist
        print("🔄 Migrating existing voucher data...")
        
        # Check if old vouchers_payable table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vouchers_payable'")
        if cursor.fetchone():
            print("📊 Found existing vouchers_payable data, migrating...")
            
            # Migrate vouchers_payable to ledger
            cursor.execute('''
                INSERT INTO ledger (type, number, date, payee_code, payee, total_amount, 
                                  description, due_date, status, created_by, created_at)
                SELECT 'VP', vp_number, created_at, company_id, company_name, amount_to_pay,
                       description, due_date, status, created_by, created_at
                FROM vouchers_payable
            ''')
            
            # Create corresponding credit/debit entries
            cursor.execute('''
                INSERT INTO ledger_credit_debit (type, number, date, acct_code, acct_description, 
                                               amount, acct_type)
                SELECT 'VP', vp_number, created_at, company_id, company_name, amount_to_pay, 'C'
                FROM vouchers_payable
            ''')
            
            # Create expense debit entries
            cursor.execute('''
                INSERT INTO ledger_credit_debit (type, number, date, acct_code, acct_description, 
                                               amount, acct_type)
                SELECT 'VP', vp_number, created_at, 
                       COALESCE(account_code, '5000'), 
                       COALESCE(description, 'General Expense'), 
                       amount_to_pay, 'D'
                FROM vouchers_payable
            ''')
            
            print("✅ Vouchers Payable migrated successfully")
        
        # Check if old check_vouchers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='check_vouchers'")
        if cursor.fetchone():
            print("📊 Found existing check_vouchers data, migrating...")
            
            # Migrate check_vouchers to ledger
            cursor.execute('''
                INSERT INTO ledger (type, number, date, payee_code, payee, total_amount, 
                                  description, status, created_by, created_at)
                SELECT 'CV', cv_number, created_at, company_id, company_name, amount_to_pay,
                       description, status, created_by, created_at
                FROM check_vouchers
            ''')
            
            print("✅ Check Vouchers migrated successfully")
        
        conn.commit()
        conn.close()
        
        print("🎉 Migration completed successfully!")
        print(f"📁 Original database backed up to: {backup_path}")
        print("🔍 Run the application to verify the migration")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.error(f"Migration error: {e}")
        return False

def main():
    """Run migration"""
    db_path = "financial_system.db"
    
    print("🚀 Database Migration to Accounting Ledger Structure")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found!")
        print("   Please run the application first to create the database.")
        return
    
    confirm = input("⚠️  This will modify your database structure. Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        return
    
    success = migrate_to_ledger_structure(db_path)
    
    if success:
        print("\n✅ Migration Summary:")
        print("   - New accounting ledger tables created")
        print("   - Double-entry bookkeeping structure in place")
        print("   - Chart of accounts populated")
        print("   - Existing voucher data migrated")
        print("   - Original database backed up")
        print("\n🚀 You can now use the full voucher management features!")
    else:
        print("\n❌ Migration failed. Check the error messages above.")

if __name__ == "__main__":
    main()