# utils/decorators.py
from functools import wraps
from flask import session, flash, redirect, url_for, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        
        if session.get('role') != 'admin':
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
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
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login', next=request.url))
            
            if session.get('role') not in roles:
                if request.is_json:
                    return jsonify({'error': f'Access denied. Required roles: {", ".join(roles)}'}), 403
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
            # Execute the function first
            result = f(*args, **kwargs)
            
            # Log the action after successful execution
            try:
                # Import here to avoid circular imports
                from core.database import DatabaseManager
                from services.audit_service import AuditService
                
                db_path = current_app.config.get('DATABASE_PATH', 'financial_system.db')
                db_manager = DatabaseManager(db_path)
                audit_service = AuditService(db_manager)
                
                audit_service.log_action(
                    user_id=session.get('user_id'),
                    action=action_name,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    details={
                        'function': f.__name__,
                        'endpoint': request.endpoint,
                        'method': request.method
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log audit action {action_name}: {e}")
            
            return result
        return decorated_function
    return decorator

def api_key_required(f):
    """Decorator for API endpoints requiring API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Get API key from config
        valid_api_key = current_app.config.get('API_KEY', 'your-secret-api-key')
        
        if api_key != valid_api_key:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(requests_per_minute=60):
    """Simple rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple rate limiting based on IP
            # In production, use Redis or similar
            ip = request.remote_addr
            
            # For now, just log and continue
            # Implement proper rate limiting with Redis if needed
            logger.info(f"Rate limit check for {ip}: {requests_per_minute} req/min")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def json_required(f):
    """Decorator to require JSON content type"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function

def validate_json(*required_fields):
    """Decorator to validate required JSON fields"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            json_data = request.get_json(silent=True)
            
            if not json_data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            missing_fields = []
            for field in required_fields:
                if field not in json_data or json_data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator