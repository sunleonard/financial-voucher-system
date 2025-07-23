# routes/users.py
"""
User Management Routes - Flask Blueprint for user-related endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import login_required, admin_required, audit_action
from services.user_service import UserService
from services.company_service import CompanyService
import logging

logger = logging.getLogger(__name__)

def create_users_blueprint(db_manager):
    """Create and configure users blueprint"""
    
    users_bp = Blueprint('users', __name__, url_prefix='/users')
    user_service = UserService(db_manager)
    company_service = CompanyService(db_manager)
    
    @users_bp.route('/')
    @admin_required
    @audit_action("VIEW_USERS_LIST")
    def list_users():
        """Display list of all users (Admin only)"""
        try:
            users = user_service.get_all_users(session.get('role'))
            user_stats = user_service.get_user_stats(session.get('role'))
            
            # Check if this is first-time setup (only admin user exists)
            other_users = [u for u in users if u['id'] != session.get('user_id') and u['is_active']]
            is_first_setup = len(other_users) == 0
            
            return render_template('users/list.html', 
                                 users=users, 
                                 stats=user_stats,
                                 current_user_id=session.get('user_id'),
                                 is_first_setup=is_first_setup)
        except Exception as e:
            logger.error(f"Error loading users list: {e}")
            flash('Error loading users list', 'error')
            return redirect(url_for('dashboard.index'))
    
    @users_bp.route('/create', methods=['GET', 'POST'])
    @admin_required
    def create_user():
        """Create new user form and handler (Admin only)"""
        
        if request.method == 'GET':
            # Get companies for dropdown
            companies = company_service.get_all_companies()
            return render_template('users/create.html', companies=companies)
        
        # Handle POST request
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            role = request.form.get('role', 'user')
            company_id = request.form.get('company_id', '').strip() or None
            
            # Validate required fields
            if not all([username, email, password]):
                flash('Username, email, and password are required', 'error')
                return redirect(request.url)
            
            # Validate password confirmation
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(request.url)
            
            # Create user
            success, message, user_id = user_service.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                company_id=company_id,
                created_by=session.get('user_id')
            )
            
            if success:
                flash(f'User "{username}" created successfully', 'success')
                return redirect(url_for('users.list_users'))
            else:
                flash(f'Failed to create user: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            flash('An error occurred while creating the user', 'error')
            return redirect(request.url)
    
    @users_bp.route('/<int:user_id>')
    @admin_required
    @audit_action("VIEW_USER_DETAILS")
    def view_user(user_id):
        """View user details (Admin only)"""
        try:
            user = user_service.get_user_by_id(user_id)
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('users.list_users'))
            
            return render_template('users/view.html', user=user)
        except Exception as e:
            logger.error(f"Error viewing user {user_id}: {e}")
            flash('Error loading user details', 'error')
            return redirect(url_for('users.list_users'))
    
    @users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def edit_user(user_id):
        """Edit user form and handler (Admin only)"""
        
        try:
            user = user_service.get_user_by_id(user_id)
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('users.list_users'))
            
            if request.method == 'GET':
                companies = company_service.get_all_companies()
                return render_template('users/edit.html', user=user, companies=companies)
            
            # Handle POST request
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            role = request.form.get('role', 'user')
            company_id = request.form.get('company_id', '').strip() or None
            is_active = 'is_active' in request.form
            
            # Validate required fields
            if not all([username, email]):
                flash('Username and email are required', 'error')
                return redirect(request.url)
            
            # Update user
            success, message = user_service.update_user(
                user_id=user_id,
                username=username,
                email=email,
                role=role,
                company_id=company_id,
                is_active=is_active,
                updated_by=session.get('user_id'),
                requester_role=session.get('role')
            )
            
            if success:
                flash(f'User "{username}" updated successfully', 'success')
                return redirect(url_for('users.list_users'))
            else:
                flash(f'Failed to update user: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error editing user {user_id}: {e}")
            flash('An error occurred while updating the user', 'error')
            return redirect(url_for('users.list_users'))
    
    @users_bp.route('/<int:user_id>/delete', methods=['POST'])
    @admin_required
    @audit_action("DELETE_USER")
    def delete_user(user_id):
        """Delete user (Admin only)"""
        try:
            # Get user info for flash message
            user = user_service.get_user_by_id(user_id)
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('users.list_users'))
            
            success, message = user_service.delete_user(
                user_id=user_id,
                deleted_by=session.get('user_id'),
                requester_role=session.get('role')
            )
            
            if success:
                flash(f'User "{user["username"]}" deleted successfully', 'success')
            else:
                flash(f'Failed to delete user: {message}', 'error')
                
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            flash('An error occurred while deleting the user', 'error')
        
        return redirect(url_for('users.list_users'))
    
    @users_bp.route('/search')
    @admin_required
    def search_users():
        """Search users (Admin only)"""
        try:
            search_term = request.args.get('q', '').strip()
            role_filter = request.args.get('role', '')
            company_filter = request.args.get('company', '')
            
            if not search_term:
                flash('Please enter a search term', 'warning')
                return redirect(url_for('users.list_users'))
            
            users = user_service.search_users(
                search_term=search_term,
                role=role_filter if role_filter else None,
                company_id=company_filter if company_filter else None,
                requester_role=session.get('role')
            )
            
            companies = company_service.get_all_companies()
            
            return render_template('users/search_results.html', 
                                 users=users, 
                                 search_term=search_term,
                                 role_filter=role_filter,
                                 company_filter=company_filter,
                                 companies=companies)
                                 
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            flash('Error occurred during search', 'error')
            return redirect(url_for('users.list_users'))
    
    # Profile Management Routes (accessible by all users)
    @users_bp.route('/profile')
    @login_required
    def profile():
        """View current user's profile"""
        try:
            user = user_service.get_user_by_id(session.get('user_id'))
            if not user:
                flash('Profile not found', 'error')
                return redirect(url_for('auth.logout'))
            
            return render_template('users/profile.html', user=user)
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            flash('Error loading profile', 'error')
            return redirect(url_for('dashboard.index'))
    
    @users_bp.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
    def edit_profile():
        """Edit current user's profile"""
        try:
            user_id = session.get('user_id')
            user = user_service.get_user_by_id(user_id)
            
            if not user:
                flash('Profile not found', 'error')
                return redirect(url_for('auth.logout'))
            
            if request.method == 'GET':
                return render_template('users/edit_profile.html', user=user)
            
            # Handle POST request
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            
            # Validate required fields
            if not all([username, email]):
                flash('Username and email are required', 'error')
                return redirect(request.url)
            
            # Update profile
            success, message = user_service.update_user(
                user_id=user_id,
                username=username,
                email=email,
                updated_by=user_id,
                requester_role=session.get('role')
            )
            
            if success:
                # Update session data
                session['username'] = username
                flash('Profile updated successfully', 'success')
                return redirect(url_for('users.profile'))
            else:
                flash(f'Failed to update profile: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error editing profile: {e}")
            flash('An error occurred while updating your profile', 'error')
            return redirect(url_for('users.profile'))
    
    @users_bp.route('/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        """Change current user's password"""
        if request.method == 'GET':
            return render_template('users/change_password.html')
        
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validate required fields
            if not all([current_password, new_password, confirm_password]):
                flash('All password fields are required', 'error')
                return redirect(request.url)
            
            # Validate password confirmation
            if new_password != confirm_password:
                flash('New passwords do not match', 'error')
                return redirect(request.url)
            
            # Change password
            success, message = user_service.change_password(
                user_id=session.get('user_id'),
                current_password=current_password,
                new_password=new_password,
                changed_by=session.get('user_id')
            )
            
            if success:
                flash('Password changed successfully', 'success')
                return redirect(url_for('users.profile'))
            else:
                flash(f'Failed to change password: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            flash('An error occurred while changing your password', 'error')
            return redirect(request.url)
    
    # API Endpoints
    @users_bp.route('/api/check-username')
    @admin_required
    def api_check_username():
        """API endpoint to check username availability"""
        username = request.args.get('username', '').strip()
        exclude_id = request.args.get('exclude_id', type=int)
        
        if not username:
            return jsonify({'available': False, 'message': 'Username is required'})
        
        available = user_service.user_model.is_username_available(username, exclude_id)
        return jsonify({
            'available': available,
            'message': 'Username is available' if available else 'Username already exists'
        })
    
    @users_bp.route('/api/check-email')
    @admin_required
    def api_check_email():
        """API endpoint to check email availability"""
        email = request.args.get('email', '').strip()
        exclude_id = request.args.get('exclude_id', type=int)
        
        if not email:
            return jsonify({'available': False, 'message': 'Email is required'})
        
        available = user_service.user_model.is_email_available(email, exclude_id)
        return jsonify({
            'available': available,
            'message': 'Email is available' if available else 'Email already exists'
        })
    
    @users_bp.route('/api/stats')
    @admin_required
    def api_user_stats():
        """API endpoint for user statistics"""
        try:
            stats = user_service.get_user_stats(session.get('role'))
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return jsonify({'error': 'Failed to get statistics'}), 500
    
    return users_bp