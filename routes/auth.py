# routes/auth.py
"""
Authentication Routes - Login, logout, and session management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.user_service import UserService
from services.audit_service import AuditService
import logging

logger = logging.getLogger(__name__)

def create_auth_blueprint(db_manager):
    """Create and configure authentication blueprint"""
    
    auth_bp = Blueprint('auth', __name__)
    user_service = UserService(db_manager)
    audit_service = AuditService(db_manager)
    
    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        """User login page and handler"""
        
        # Redirect if already logged in
        if 'user_id' in session:
            return redirect(url_for('dashboard.index'))
        
        if request.method == 'GET':
            return render_template('auth/login.html')
        
        # Handle POST request
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember_me = 'remember_me' in request.form
            
            # Validate required fields
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('auth/login.html')
            
            # Attempt authentication
            success, message, user_data = user_service.authenticate_user(
                username=username,
                password=password,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            if success and user_data:
                # Set session data
                session.permanent = remember_me
                session['user_id'] = user_data['id']
                session['username'] = user_data['username']
                session['email'] = user_data['email']
                session['role'] = user_data['role']
                session['company_id'] = user_data['company_id']
                
                # Flash welcome message
                flash(f'Welcome back, {user_data["username"]}!', 'success')
                
                # Smart routing for admins
                if user_data['role'] == 'admin':
                    # Check if there are other users besides this admin
                    from services.user_service import UserService
                    user_service_check = UserService(db_manager)
                    all_users = user_service_check.get_all_users(user_data['role'])
                    
                    # Count active users excluding the current admin
                    other_users = [u for u in all_users if u['id'] != user_data['id'] and u['is_active']]
                    
                    if len(other_users) == 0:
                        # Only admin exists, redirect to user management for setup
                        flash('Welcome! You\'re the only user in the system. Let\'s start by adding more users.', 'info')
                        next_page = url_for('users.list_users')
                    else:
                        # Other users exist, go to dashboard
                        next_page = url_for('dashboard.index')
                else:
                    # Regular users always go to dashboard
                    next_page = url_for('dashboard.index')
                
                # Check for intended redirect page
                intended_page = request.args.get('next')
                if intended_page and intended_page.startswith('/'):
                    return redirect(intended_page)
                else:
                    return redirect(next_page)
            else:
                flash(message, 'error')
                return render_template('auth/login.html', username=username)
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('auth/login.html')
    
    @auth_bp.route('/logout')
    def logout():
        """User logout"""
        try:
            username = session.get('username', 'Unknown')
            user_id = session.get('user_id')
            
            # Log logout action
            if user_id:
                audit_service.log_action(
                    user_id=user_id,
                    action="LOGOUT",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            
            # Clear session
            session.clear()
            
            flash(f'Goodbye, {username}! You have been logged out.', 'info')
            logger.info(f"User logged out: {username}")
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            session.clear()
            flash('You have been logged out.', 'info')
        
        return redirect(url_for('auth.login'))
    
    @auth_bp.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """Forgot password page (placeholder for future implementation)"""
        if request.method == 'GET':
            return render_template('auth/forgot_password.html')
        
        # For now, just show a message
        email = request.form.get('email', '').strip()
        if email:
            flash('Password reset functionality will be implemented soon. Please contact your administrator.', 'info')
        else:
            flash('Please enter your email address.', 'error')
        
        return render_template('auth/forgot_password.html')
    
    @auth_bp.route('/session-check')
    def session_check():
        """API endpoint to check session status"""
        if 'user_id' in session:
            return {
                'authenticated': True,
                'user': {
                    'id': session.get('user_id'),
                    'username': session.get('username'),
                    'role': session.get('role'),
                    'company_id': session.get('company_id')
                }
            }
        else:
            return {'authenticated': False}
    
    @auth_bp.route('/extend-session', methods=['POST'])
    def extend_session():
        """Extend user session"""
        if 'user_id' in session:
            session.permanent = True
            return {'success': True, 'message': 'Session extended'}
        else:
            return {'success': False, 'message': 'Not authenticated'}, 401
    
    return auth_bp