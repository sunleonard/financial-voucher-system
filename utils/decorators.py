from functools import wraps
from flask import session, flash, redirect, url_for, request, jsonify, g
import logging

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            if session.get('role') not in roles:
                flash(f'Access denied. Required roles: {", ".join(roles)}', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def audit_action(action_name: str):
    """Decorator to automatically log actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from services.audit_service import AuditService
            
            # Execute the function
            result = f(*args, **kwargs)
            
            # Log the action
            try:
                audit_service = AuditService()
                audit_service.log_action(
                    user_id=session.get('user_id'),
                    action=action_name,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    details={'function': f.__name__, 'args': str(args)}
                )
            except Exception as e:
                logger.error(f"Failed to log audit action: {e}")
            
            return result
        return decorated_function
    return decorator

def api_key_required(f):
    """Decorator for API endpoints requiring API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Validate API key here
        # This is a simplified example - implement proper API key validation
        if api_key != 'your-api-key':
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function