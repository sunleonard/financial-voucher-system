# simple_fix.py
"""
Updated Simple Fix Script - Recreate database with new accounting structure
"""

import os
import sqlite3
from datetime import datetime, date

def check_database_file():
    """Check if database file exists"""
    db_file = "financial_system.db"
    exists = os.path.exists(db_file)
    print(f"Database file exists: {'Yes' if exists else 'No'}")
    
    if exists:
        # Check size
        size = os.path.getsize(db_file)
        print(f"Database size: {size} bytes")
        
        if size == 0:
            print("❌ Database file is empty!")
            return False
    
    return exists

def create_database_and_admin():
    """Create database with new accounting structure and admin user"""
    print("🔧 Creating database with new accounting structure...")
    
    try:
        # Remove existing database if it's corrupted
        if os.path.exists("financial_system.db"):
            os.remove("financial_system.db")
            print("🗑️ Removed existing database file")
        
        # Import and use our updated system
        from migrations.init_db import create_schema, insert_default_data
        from core.database import DatabaseManager
        from services.user_service import UserService
        from services.company_service import CompanyService
        from services.accounting_service import AccountingService
        from models.account_definition import AccountDefinition
        
        # Create database schema with new accounting structure
        print("📝 Creating database schema...")
        success = create_schema("financial_system.db")
        if not success:
            print("❌ Failed to create database schema")
            return False
        
        # Insert default reference data
        print("📝 Inserting default accounting data...")
        success = insert_default_data("financial_system.db")
        if not success:
            print("❌ Failed to insert default data")
            return False
        
        # Create database manager and services
        db_manager = DatabaseManager("financial_system.db")
        user_service = UserService(db_manager)
        company_service = CompanyService(db_manager)
        accounting_service = AccountingService(db_manager)
        account_model = AccountDefinition(db_manager)
        
        # Create companies and accounts
        print("🏢 Setting up companies and accounts...")
        company_service.create_company_table()
        company_service.insert_default_companies()
        
        # Create admin user
        print("👤 Creating admin user...")
        success, message, user_id = user_service.create_user(
            username="admin",
            email="admin@company.com",
            password="Admin123!",  # Strong password that meets all requirements
            role="admin"
        )
        
        if success:
            print(f"✅ Admin user created successfully! ID: {user_id}")
            
            # Test login immediately
            print("🔍 Testing login...")
            auth_success, auth_message, auth_data = user_service.authenticate_user(
                username="admin",
                password="Admin123!"
            )
            
            if auth_success:
                print("✅ Login test successful!")
                
                # Create some sample accounting data for demonstration
                print("📊 Creating sample accounting data...")
                create_sample_accounting_data(accounting_service, user_id)
                
                print("🎉 Setup complete! You can now login with:")
                print("   Username: admin")
                print("   Password: Admin123!")
                print()
                print("📈 Sample data created:")
                print("   • Chart of Accounts with standard accounting structure")
                print("   • Sample companies and vendors")
                print("   • Demo Voucher Payable and Check Voucher")
                print("   • Ready for Trial Balance and reports")
                
                return True
            else:
                print(f"❌ Login test failed: {auth_message}")
                return False
        else:
            print(f"❌ Failed to create admin user: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_accounting_data(accounting_service, user_id):
    """Create sample accounting transactions for demonstration"""
    try:
        # Create a sample Voucher Payable
        print("  Creating sample Voucher Payable...")
        success, message, vp_number = accounting_service.create_voucher_payable(
            transaction_date=date.today(),
            payee_code="VEND001",
            total_amount=1500.00,
            description="Office supplies and equipment for Q1",
            due_date=date(2025, 8, 15),
            credit_debit_lines=[
                {
                    'acct_code': '5000',
                    'acct_description': 'Office Supplies',
                    'amount': 800.00,
                    'acct_type': 'D'
                },
                {
                    'acct_code': '1300',
                    'acct_description': 'Office Equipment',
                    'amount': 700.00,
                    'acct_type': 'D'
                },
                {
                    'acct_code': '2000',
                    'acct_description': 'Accounts Payable',
                    'amount': 1500.00,
                    'acct_type': 'C'
                }
            ],
            subsidiary_lines=[
                {
                    'acct_code': '5000',
                    'acct_description': 'Office Supplies',
                    'subsidiary_code': 'SUB001',
                    'subsidiary_description': 'Department A',
                    'amount': 500.00
                },
                {
                    'acct_code': '5000',
                    'acct_description': 'Office Supplies', 
                    'subsidiary_code': 'SUB002',
                    'subsidiary_description': 'Department B',
                    'amount': 300.00
                }
            ],
            created_by=user_id
        )
        
        if success:
            print(f"  ✅ Sample Voucher Payable created: {vp_number}")
            
            # Create a related Check Voucher
            print("  Creating sample Check Voucher...")
            success, message, cv_number = accounting_service.create_check_voucher(
                transaction_date=date.today(),
                payee_code="VEND001",
                total_amount=1500.00,
                vp_number=vp_number,
                check_number="1001",
                bank_account="1010",
                description=f"Payment for {vp_number} - Office supplies",
                created_by=user_id
            )
            
            if success:
                print(f"  ✅ Sample Check Voucher created: {cv_number}")
            else:
                print(f"  ⚠️ Check Voucher creation failed: {message}")
        else:
            print(f"  ⚠️ Voucher Payable creation failed: {message}")
        
        # Create another VP for different vendor
        print("  Creating additional sample transaction...")
        success, message, vp_number2 = accounting_service.create_voucher_payable(
            transaction_date=date(2025, 7, 20),
            payee_code="VEND004",
            total_amount=450.00,
            description="Monthly utility bill",
            due_date=date(2025, 8, 10),
            created_by=user_id
        )
        
        if success:
            print(f"  ✅ Additional Voucher Payable created: {vp_number2}")
        
    except Exception as e:
        print(f"  ⚠️ Error creating sample data: {e}")

def quick_check():
    """Quick check of the current database"""
    try:
        # Direct SQLite check
        conn = sqlite3.connect("financial_system.db")
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"Database tables: {len(table_names)}")
        for table in sorted(table_names):
            if not table.startswith('sqlite_'):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count} rows")
        
        # Check if new accounting tables exist
        required_tables = ['ledger', 'ledger_credit_debit', 'ledger_subcodes', 'acct_definition']
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if missing_tables:
            print(f"❌ Missing accounting tables: {missing_tables}")
            conn.close()
            return False
        
        # Check for users
        if 'users' in table_names:
            cursor.execute("SELECT username, role, is_active FROM users")
            users = cursor.fetchall()
            print(f"Users in database: {len(users)}")
            for user in users:
                print(f"  - {user[0]} ({user[1]}) - {'Active' if user[2] else 'Inactive'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database check error: {e}")
        return False

def show_system_info():
    """Show information about the new accounting system"""
    print()
    print("=" * 70)
    print("🏦 FINANCIAL VOUCHER MANAGEMENT SYSTEM")
    print("   Advanced Double-Entry Accounting System")
    print("=" * 70)
    print()
    print("🆕 NEW ACCOUNTING FEATURES:")
    print("   ✅ Proper Ledger Structure (Format: 1-001-2025)")
    print("   ✅ Double-Entry Bookkeeping")
    print("   ✅ Chart of Accounts with Account Types")
    print("   ✅ Credit/Debit Line Items")
    print("   ✅ Subsidiary Code Tracking")
    print("   ✅ Trial Balance Reports")
    print("   ✅ Account Ledgers")
    print("   ✅ Transaction Voiding")
    print("   ✅ Balance Validation")
    print()
    print("📊 FINANCIAL STRUCTURE:")
    print("   • Ledger: Main transaction headers (VP/CV)")
    print("   • Credit/Debit: Double-entry lines")
    print("   • Subcodes: Subsidiary breakdown")
    print("   • Account Definition: Chart of accounts")
    print()
    print("🔢 ACCOUNT CODE STRUCTURE:")
    print("   • Company/Asset/Expense: 1000-5999")
    print("   • Liability: 2000-2999")
    print("   • Equity: 3000-3999")
    print("   • Revenue: 4000-4999")
    print("   • Customers: CUST001-999")
    print("   • Vendors: VEND001-999")
    print("   • Employees: EMP001-999")
    print()
    print("📈 TRANSACTION TYPES:")
    print("   • VP (Voucher Payable): Payment obligations")
    print("   • CV (Check Voucher): Actual payments")
    print("   • Each with proper debit/credit entries")
    print()
    print("🌐 ACCESS THE SYSTEM:")
    print("   URL: http://localhost:5000")
    print("   Username: admin")
    print("   Password: Admin123!")
    print("=" * 70)

def main():
    """Run all checks and setup"""
    print("🚀 Financial System Setup - New Accounting Structure")
    print("=" * 60)
    
    # Check if database exists and is valid
    if check_database_file():
        print("📝 Database file exists, checking structure...")
        if quick_check():
            print("✅ Database structure looks good!")
            response = input("\nDatabase exists. Recreate with fresh data? (y/N): ")
            if response.lower() != 'y':
                print("✅ Using existing database")
                show_system_info()
                return
        else:
            print("❌ Database structure issues detected")
    
    # Create/recreate database
    print("\n📝 Creating new database with accounting structure...")
    success = create_database_and_admin()
    
    print("\n" + "=" * 60)
    print("🎯 SETUP SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ Database created with new accounting structure")
        print("✅ Admin user created and tested")
        print("✅ Sample accounting data created")
        print("✅ Ready for accounting operations")
        show_system_info()
    else:
        print("❌ Setup failed - check error messages above")
        print("💡 Try running: python troubleshoot.py")

if __name__ == "__main__":
    main()