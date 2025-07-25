# app.py
"""
Main Flask Application - Financial Voucher Management System
Entry point for the web application with updated accounting structure
"""

import os
from flask import Flask, redirect, url_for, session
from core.database import DatabaseManager
from core.logger import setup_logging
from config import config
import logging

# Import blueprints
from routes.auth import create_auth_blueprint
from routes.users import create_users_blueprint
from routes.dashboard import create_dashboard_blueprint
from routes.accounting import create_accounting_blueprint

def create_app(config_name=None):
    """Application factory pattern"""
    
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Setup logging
    setup_logging(
        log_level=app.config['LOG_LEVEL'],
        log_file=app.config['LOG_FILE']
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Financial Voucher Management System in {config_name} mode")
    
    # Initialize database with new accounting structure
    db_manager = DatabaseManager(app.config['DATABASE_PATH'])
    
    # Create default data if needed
    try:
        from services.user_service import UserService
        from services.company_service import CompanyService
        from models.account_definition import AccountDefinition
        from models.ledger import Ledger
        from models.ledger_credit_debit import LedgerCreditDebit
        from models.ledger_subcodes import LedgerSubcodes
        
        # Initialize all models
        user_service = UserService(db_manager)
        company_service = CompanyService(db_manager)
        account_model = AccountDefinition(db_manager)
        ledger_model = Ledger(db_manager)
        credit_debit_model = LedgerCreditDebit(db_manager)
        subcodes_model = LedgerSubcodes(db_manager)
        
        # Create tables if they don't exist
        company_service.create_company_table()
        account_model.create_table()
        ledger_model.create_table()
        credit_debit_model.create_table()
        subcodes_model.create_table()
        
        # Insert default companies and accounts
        company_service.insert_default_companies()
        
        # Create default admin user
        success, message, user_id = user_service.create_user(
            username="admin",
            email="admin@company.com", 
            password="Admin123!",  # Strong password that meets security requirements
            role="admin"
        )
        if success:
            logger.info("Default admin user created")
        else:
            logger.info("Default admin user already exists")
            
    except Exception as e:
        logger.warning(f"Could not create default data: {e}")
    
    # Register blueprints
    app.register_blueprint(create_auth_blueprint(db_manager))
    app.register_blueprint(create_users_blueprint(db_manager))
    app.register_blueprint(create_dashboard_blueprint(db_manager))
    app.register_blueprint(create_accounting_blueprint(db_manager))
    
    # Root route with smart routing
    @app.route('/')
    def index():
        """Root route - redirect based on authentication status and user type"""
        if 'user_id' in session:
            # Check if user is admin and if this is first-time setup
            if session.get('role') == 'admin':
                try:
                    # Check if there are any transactions in the system
                    from services.accounting_service import AccountingService
                    accounting_service = AccountingService(db_manager)
                    
                    recent_transactions = accounting_service.ledger.get_all(limit=1)
                    
                    if not recent_transactions:
                        # No transactions yet, might want to go to accounting dashboard
                        return redirect(url_for('accounting.dashboard'))
                    else:
                        # Has transactions, go to main dashboard
                        return redirect(url_for('dashboard.index'))
                except:
                    # Fallback to main dashboard
                    return redirect(url_for('dashboard.index'))
            else:
                # Regular users go to main dashboard
                return redirect(url_for('dashboard.index'))
        
        # Not logged in, go to login
        return redirect(url_for('auth.login'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 error: {error}")
        if 'user_id' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error: {error}")
        if 'user_id' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # Context processors for templates
    @app.context_processor
    def utility_processor():
        """Make utility functions available in templates"""
        from datetime import datetime, date
        
        def as_date(date_string):
            """Convert date string to date object"""
            if isinstance(date_string, str):
                try:
                    return datetime.strptime(date_string, '%Y-%m-%d').date()
                except:
                    return None
            return date_string
        
        return {
            'enumerate': enumerate,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'date': date,
            'datetime': datetime,
            'as_date': as_date
        }
    
    # Session configuration
    @app.before_request
    def before_request():
        """Before request handler for session management"""
        from flask import request
        
        # Make session permanent if remember me was checked
        if 'user_id' in session:
            session.permanent = True
    
    # Custom filters for templates
    @app.template_filter('currency')
    def currency_filter(amount):
        """Format amount as currency"""
        try:
            return f"${float(amount):,.2f}"
        except (ValueError, TypeError):
            return "$0.00"
    
    @app.template_filter('account_type_badge')
    def account_type_badge(account_type):
        """Return Bootstrap badge class for account type"""
        type_classes = {
            'Company': 'bg-primary',
            'Customer': 'bg-success', 
            'Employee': 'bg-info',
            'Subsidiary': 'bg-warning'
        }
        return type_classes.get(account_type, 'bg-secondary')
    
    @app.template_filter('transaction_type_icon')
    def transaction_type_icon(transaction_type):
        """Return Font Awesome icon for transaction type"""
        icons = {
            'VP': 'fas fa-file-invoice',
            'CV': 'fas fa-check'
        }
        return icons.get(transaction_type, 'fas fa-file')
    
    logger.info("Flask application created successfully with accounting features")
    return app

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    print("=" * 70)
    print("🏦 FINANCIAL VOUCHER MANAGEMENT SYSTEM")
    print("   Advanced Accounting & Ledger Management")
    print("=" * 70)
    print("🔑 Default Login Credentials:")
    print("   Username: admin")
    print("   Password: Admin123!")
    print("=" * 70)
    print("🌐 Server Info:")
    print("   URL: http://localhost:5000")
    print("   Environment: Development")
    print("   Debug Mode: ON")
    print("=" * 70)
    print("📊 Features Available:")
    print("   ✅ User Management (Admin)")
    print("   ✅ Authentication & Authorization")
    print("   ✅ Profile Management")
    print("   ✅ Audit Logging")
    print("   ✅ Accounting Dashboard")
    print("   ✅ Chart of Accounts")
    print("   ✅ Vouchers Payable (VP)")
    print("   ✅ Check Vouchers (CV)")
    print("   ✅ Double-Entry Bookkeeping")
    print("   ✅ Subsidiary Code Tracking")
    print("   ✅ Trial Balance Reports")
    print("   ✅ Account Ledgers")
    print("=" * 70)
    print("🎯 New Accounting Features:")
    print("   • Proper ledger structure with number format: 1-001-2025")
    print("   • Credit/Debit entries following accounting principles")
    print("   • Subsidiary code breakdown for detailed tracking")
    print("   • Account definitions with types (Company/Customer/Employee)")
    print("   • Balance validation and trial balance reports")
    print("   • Transaction voiding and audit trail")
    print("=" * 70)
    print("🚀 Starting development server...")
    print("   Press Ctrl+C to stop")
    print("=" * 70)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )