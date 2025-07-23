# troubleshoot.py
"""
Troubleshooting script to check if all components are working
"""

import os
import sys
import importlib.util

def check_file_exists(filepath):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {filepath}")
    return exists

def check_import(module_name, filepath=None):
    """Check if a module can be imported"""
    try:
        if filepath:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            __import__(module_name)
        print(f"✅ {module_name} imported successfully")
        return True
    except Exception as e:
        print(f"❌ {module_name} import failed: {e}")
        return False

def check_directory_structure():
    """Check if all required directories exist"""
    print("🔍 Checking directory structure...")
    
    required_dirs = [
        "core",
        "models", 
        "services",
        "routes",
        "templates",
        "templates/auth",
        "templates/dashboard", 
        "templates/users",
        "utils",
        "migrations",
        "logs"
    ]
    
    all_good = True
    for directory in required_dirs:
        exists = os.path.exists(directory)
        if not exists:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created directory: {directory}")
        else:
            print(f"✅ {directory}/")
    
    return all_good

def check_required_files():
    """Check if all required Python files exist"""
    print("\n🔍 Checking required files...")
    
    required_files = [
        "app.py",
        "config.py",
        "core/__init__.py",
        "core/database.py",
        "core/logger.py", 
        "core/security.py",
        "models/__init__.py",
        "models/user.py",
        "services/__init__.py",
        "services/user_service.py",
        "services/company_service.py",
        "services/dashboard_service.py",
        "services/audit_service.py",
        "routes/__init__.py",
        "routes/auth.py",
        "routes/users.py",
        "routes/dashboard.py",
        "utils/__init__.py",
        "utils/decorators.py",
        "migrations/__init__.py",
        "migrations/init_db.py"
    ]
    
    all_good = True
    for filepath in required_files:
        if not check_file_exists(filepath):
            all_good = False
            
            # Create missing __init__.py files
            if filepath.endswith("__init__.py"):
                with open(filepath, 'w') as f:
                    f.write("# This file makes Python treat the directory as a package\n")
                print(f"📝 Created {filepath}")
    
    return all_good

def check_template_files():
    """Check if required template files exist"""
    print("\n🔍 Checking template files...")
    
    required_templates = [
        "templates/base.html",
        "templates/auth/login.html",
        "templates/auth/forgot_password.html",
        "templates/dashboard/index.html",
        "templates/users/list.html",
        "templates/users/create.html",
        "templates/users/edit.html",
        "templates/users/view.html",
        "templates/users/profile.html",
        "templates/users/edit_profile.html",
        "templates/users/change_password.html",
        "templates/users/search_results.html"
    ]
    
    all_good = True
    for template in required_templates:
        if not check_file_exists(template):
            all_good = False
    
    return all_good

def check_imports():
    """Check if all modules can be imported"""
    print("\n🔍 Checking imports...")
    
    # Check external dependencies
    external_modules = ["flask", "sqlite3", "hashlib", "json", "logging", "datetime"]
    
    for module in external_modules:
        check_import(module)
    
    # Check internal modules
    internal_modules = [
        ("core.database", "core/database.py"),
        ("core.logger", "core/logger.py"),
        ("core.security", "core/security.py"),
        ("models.user", "models/user.py"),
        ("services.user_service", "services/user_service.py"),
        ("services.company_service", "services/company_service.py"),
        ("utils.decorators", "utils/decorators.py")
    ]
    
    for module_name, filepath in internal_modules:
        if os.path.exists(filepath):
            check_import(module_name, filepath)

def check_database():
    """Test database creation"""
    print("\n🔍 Testing database creation...")
    
    try:
        from migrations.init_db import create_schema, insert_default_data
        
        test_db = "test_check.db"
        
        if create_schema(test_db):
            print("✅ Database schema creation works")
            
            if insert_default_data(test_db):
                print("✅ Default data insertion works")
            else:
                print("❌ Default data insertion failed")
            
            # Cleanup
            if os.path.exists(test_db):
                os.remove(test_db)
                print("✅ Test database cleaned up")
        else:
            print("❌ Database schema creation failed")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")

def main():
    """Run all checks"""
    print("🚀 Financial Voucher Management System - Troubleshooting")
    print("=" * 60)
    
    # Check directory structure
    check_directory_structure()
    
    # Check required files
    files_ok = check_required_files()
    
    # Check templates
    templates_ok = check_template_files()
    
    # Check imports
    check_imports()
    
    # Test database
    check_database()
    
    print("\n" + "=" * 60)
    print("🎯 SUMMARY")
    print("=" * 60)
    
    if files_ok and templates_ok:
        print("✅ All core files are present")
        print("🚀 You should be able to run: python app.py")
        print("🌐 Then visit: http://localhost:5000")
        print("🔑 Login with: admin / Admin123!")
    else:
        print("❌ Some files are missing")
        print("📝 Create the missing files shown above")
    
    print("\n💡 If you still get errors:")
    print("   1. Check the console output for specific error messages")
    print("   2. Make sure you're in the correct directory")
    print("   3. Verify Flask is installed: pip install flask")
    print("   4. Check Python version: python --version (should be 3.7+)")

if __name__ == "__main__":
    main()