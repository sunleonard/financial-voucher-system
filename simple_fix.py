# simple_fix.py
"""
Simple script to fix login issues by recreating the admin user
"""

import os
import sqlite3

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
    """Create database and admin user from scratch"""
    print("🔧 Creating database and admin user from scratch...")
    
    try:
        # Remove existing database if it's corrupted
        if os.path.exists("financial_system.db"):
            os.remove("financial_system.db")
            print("🗑️ Removed existing database file")
        
        # Import and use our system
        from migrations.init_db import create_schema, insert_default_data
        from core.database import DatabaseManager
        from services.user_service import UserService
        from services.company_service import CompanyService
        
        # Create database schema
        print("📝 Creating database schema...")
        success = create_schema("financial_system.db")
        if not success:
            print("❌ Failed to create database schema")
            return False
        
        # Insert default data
        print("📝 Inserting default data...")
        success = insert_default_data("financial_system.db")
        if not success:
            print("❌ Failed to insert default data")
            return False
        
        # Create database manager and services
        db_manager = DatabaseManager("financial_system.db")
        user_service = UserService(db_manager)
        company_service = CompanyService(db_manager)
        
        # Create companies table and default companies
        print("🏢 Creating companies...")
        company_service.create_company_table()
        company_service.insert_default_companies()
        
        # Create admin user with a stronger password that meets requirements
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
                password="Admin123!"  # Use the new strong password
            )
            
            if auth_success:
                print("✅ Login test successful!")
                print("🎉 You can now login with:")
                print("   Username: admin")
                print("   Password: Admin123!")
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

def quick_check():
    """Quick check of the current database"""
    try:
        # Direct SQLite check
        conn = sqlite3.connect("financial_system.db")
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone() is not None
        print(f"Users table exists: {'Yes' if table_exists else 'No'}")
        
        if table_exists:
            # Check users
            cursor.execute("SELECT username, role, is_active FROM users")
            users = cursor.fetchall()
            print(f"Users in database: {len(users)}")
            for user in users:
                print(f"  - {user[0]} ({user[1]}) - {'Active' if user[2] else 'Inactive'}")
        
        conn.close()
        return table_exists
        
    except Exception as e:
        print(f"❌ Database check error: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Simple Login Fix")
    print("=" * 30)
    
    # Check if database file exists
    if not check_database_file():
        print("📝 Database file missing or empty, creating new one...")
        create_database_and_admin()
    else:
        print("📝 Database file exists, checking contents...")
        if quick_check():
            print("🔍 Database seems OK, but let's recreate admin user...")
            create_database_and_admin()
        else:
            print("📝 Database issues detected, recreating...")
            create_database_and_admin()

if __name__ == "__main__":
    main()