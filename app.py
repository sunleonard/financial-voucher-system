# app.py
"""
Main Flask Application - Financial Voucher Management System
Entry point for the web application
"""

import os
from flask import Flask, redirect, url_for, session
from core.database import DatabaseManager
from core.logger import setup_logging
from config import config
import logging

# Import blueprints\
from routes.auth import create_auth_blueprint
from routes.users import create_users_blueprint
from routes.dashboard import create_dashboard_blueprint

# TODO: Create these blueprints later
# from routes.companies import create_companies_blueprint
# from routes.vouchers import create_vouchers_blueprint
# from routes.bank_memos import create_bank_memos_blueprint
# from routes.purchase_orders import create_purchase_orders_blueprint

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
    
    # Initialize database
    db_manager = DatabaseManager(app.config['DATABASE_PATH'])
    
    # Create default admin user and companies if not exists
    try:
        from services.user_service import UserService
        from services.company_service import CompanyService
        
        user_service = UserService(db_manager)
        company_service = CompanyService(db_manager)
        
        # Create companies table
        company_service.create_company_table()
        
        # Insert default companies
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
    
    # TODO: Register these blueprints when created
    # app.register_blueprint(create_companies_blueprint(db_manager))
    # app.register_blueprint(create_vouchers_blueprint(db_manager))
    # app.register_blueprint(create_bank_memos_blueprint(db_manager))
    # app.register_blueprint(create_purchase_orders_blueprint(db_manager))
    
    # Root route
    @app.route('/')
    def index():
        """Root route - redirect based on authentication status"""
        if 'user_id' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 error: {error}")
        return redirect(url_for('dashboard.index' if 'user_id' in session else 'auth.login'))
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error: {error}")
        return redirect(url_for('dashboard.index' if 'user_id' in session else 'auth.login'))
    
    # Context processors for templates
    @app.context_processor
    def utility_processor():
        """Make utility functions available in templates"""
        return {
            'enumerate': enumerate,
            'len': len,
            'str': str,
            'int': int,
            'float': float
        }
    
    # Session configuration
    @app.before_request
    def before_request():
        """Before request handler for session management"""
        from flask import request
        
        # Make session permanent if remember me was checked
        if 'user_id' in session:
            session.permanent = True
    
    logger.info("Flask application created successfully")
    return app

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    print("=" * 60)
    print("🏦 FINANCIAL VOUCHER MANAGEMENT SYSTEM")
    print("=" * 60)
    print("🔑 Default Login Credentials:")
    print("   Username: admin")
    print("   Password: Admin123!")
    print("=" * 60)
    print("🌐 Server Info:")
    print("   URL: http://localhost:5000")
    print("   Environment: Development")
    print("   Debug Mode: ON")
    print("=" * 60)
    print("📊 Features Available:")
    print("   ✅ User Management (Admin)")
    print("   ✅ Authentication & Authorization")
    print("   ✅ Profile Management")
    print("   ✅ Audit Logging")
    print("   🔄 Dashboard (Coming Soon)")
    print("   🔄 Voucher Management (Coming Soon)")
    print("   🔄 Company Management (Coming Soon)")
    print("=" * 60)
    print("🚀 Starting development server...")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )