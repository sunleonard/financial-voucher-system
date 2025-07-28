# services/user_service.py
"""
User Service - Business logic for user management
"""

from typing import Optional, Dict, List, Tuple  # ← ADD THIS IMPORT LINE
import logging
from datetime import datetime
from core.security import SecurityManager
from models.user import User
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

class UserService:
    """User management service"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.user_model = User(db_manager)
        self.security = SecurityManager()
        self.audit = AuditService(db_manager)
    
    def create_user(self, username: str, email: str, password: str, 
                   role: str = 'user', company_id: str = None, 
                   created_by: int = None) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new user with validation
        Returns: (success, message, user_id)
        """
        
        # Validate input
        validation_result = self._validate_user_input(username, email, password, role)
        if not validation_result[0]:
            return False, validation_result[1], None
        
        # Check if username already exists
        if not self.user_model.is_username_available(username):
            return False, "Username already exists", None
        
        # Check if email already exists
        if not self.user_model.is_email_available(email):
            return False, "Email already exists", None
        
        # Hash password
        password_hash, salt = self.security.hash_password(password)
        
        # Create user
        user_id = self.user_model.create(username, email, password_hash, salt, role, company_id)
        
        if user_id:
            # Log audit trail
            self.audit.log_action(
                user_id=created_by,
                action="CREATE_USER",
                table_name="users",
                record_id=str(user_id),
                new_values={
                    'username': username,
                    'email': email,
                    'role': role,
                    'company_id': company_id
                }
            )
            
            logger.info(f"User created successfully: {username} (ID: {user_id})")
            return True, "User created successfully", user_id
        else:
            return False, "Failed to create user", None
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate user login
        Returns: (success, message, user_data)
        """
        
        # Get user by username
        user = self.user_model.get_by_username(username)
        
        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            return False, "Invalid username or password", None
        
        # Check if account is active
        if not user['is_active']:
            logger.warning(f"Login attempt on inactive account: {username}")
            return False, "Account is disabled", None
        
        # Check if account is locked
        if user.get('locked_until') and user['locked_until'] > datetime.now().isoformat():
            logger.warning(f"Login attempt on locked account: {username}")
            return False, "Account is temporarily locked due to failed login attempts", None
        
        # Verify password
        if not self.security.verify_password(password, user['password_hash'], user['salt']):
            # Increment failed attempts
            self.user_model.increment_failed_attempts(user['id'])
            
            # Log failed attempt
            self.audit.log_action(
                user_id=user['id'],
                action="LOGIN_FAILED",
                ip_address=ip_address,
                user_agent=user_agent,
                details={'reason': 'invalid_password'}
            )
            
            logger.warning(f"Failed login attempt for user: {username}")
            return False, "Invalid username or password", None
        
        # Update last login
        self.user_model.update_last_login(user['id'])
        
        # Log successful login
        self.audit.log_action(
            user_id=user['id'],
            action="LOGIN_SUCCESS",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Return user data (excluding sensitive info)
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'company_id': user['company_id']
        }
        
        logger.info(f"User logged in successfully: {username}")
        return True, "Login successful", user_data
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        return self.user_model.get_by_id(user_id)
    
    def get_all_users(self, requester_role: str = None) -> List[Dict]:
        """Get all users (admin only)"""
        if requester_role != 'admin':
            logger.warning("Non-admin user attempted to access all users")
            return []
        
        return self.user_model.get_all()
    
    def update_user(self, user_id: int, username: str = None, email: str = None,
                   role: str = None, company_id: str = None, is_active: bool = None,
                   updated_by: int = None, requester_role: str = None) -> Tuple[bool, str]:
        """
        Update user information
        Returns: (success, message)
        """
        
        # Get current user data for audit trail
        current_user = self.user_model.get_by_id(user_id)
        if not current_user:
            return False, "User not found"
        
        # Permission check
        if requester_role != 'admin' and updated_by != user_id:
            return False, "Permission denied"
        
        # Validate updates
        updates = {}
        
        if username is not None:
            if not self._validate_username(username):
                return False, "Invalid username format"
            if not self.user_model.is_username_available(username, user_id):
                return False, "Username already exists"
            updates['username'] = username
        
        if email is not None:
            if not self._validate_email(email):
                return False, "Invalid email format"
            if not self.user_model.is_email_available(email, user_id):
                return False, "Email already exists"
            updates['email'] = email
        
        if role is not None:
            if requester_role != 'admin':
                return False, "Only admins can change user roles"
            if role not in ['admin', 'user']:
                return False, "Invalid role"
            updates['role'] = role
        
        if company_id is not None:
            updates['company_id'] = company_id
        
        if is_active is not None:
            if requester_role != 'admin':
                return False, "Only admins can activate/deactivate users"
            updates['is_active'] = is_active
        
        if not updates:
            return False, "No valid updates provided"
        
        # Perform update
        success = self.user_model.update(user_id, **updates)
        
        if success:
            # Log audit trail
            self.audit.log_action(
                user_id=updated_by,
                action="UPDATE_USER",
                table_name="users",
                record_id=str(user_id),
                old_values=current_user,
                new_values=updates
            )
            
            logger.info(f"User {user_id} updated by user {updated_by}")
            return True, "User updated successfully"
        else:
            return False, "Failed to update user"
    
    def delete_user(self, user_id: int, deleted_by: int = None, 
                   requester_role: str = None) -> Tuple[bool, str]:
        """
        Delete user (admin only)
        Returns: (success, message)
        """
        
        if requester_role != 'admin':
            return False, "Only admins can delete users"
        
        # Get user data for audit trail
        user = self.user_model.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        # Prevent self-deletion
        if user_id == deleted_by:
            return False, "Cannot delete your own account"
        
        # Soft delete
        success = self.user_model.soft_delete(user_id)
        
        if success:
            # Log audit trail
            self.audit.log_action(
                user_id=deleted_by,
                action="DELETE_USER",
                table_name="users",
                record_id=str(user_id),
                old_values=user
            )
            
            logger.info(f"User {user_id} deleted by user {deleted_by}")
            return True, "User deleted successfully"
        else:
            return False, "Failed to delete user"
    
    def change_password(self, user_id: int, current_password: str, 
                       new_password: str, changed_by: int = None) -> Tuple[bool, str]:
        """
        Change user password
        Returns: (success, message)
        """
        try:
            # Get user with password data
            user = self.user_model.get_by_username_with_password(user_id)
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not self.security.verify_password(current_password, user['password_hash'], user['salt']):
                # Log failed attempt
                self.audit.log_action(
                    user_id=user_id,
                    action="PASSWORD_CHANGE_FAILED",
                    details={'reason': 'invalid_current_password'}
                )
                return False, "Current password is incorrect"
            
            # Validate new password
            is_strong, errors = self.security.validate_password_strength(new_password)
            if not is_strong:
                return False, "; ".join(errors)
            
            # Hash new password
            new_hash, new_salt = self.security.hash_password(new_password)
            
            # Update password
            success = self.user_model.update_password(user_id, new_hash, new_salt)
            
            if success:
                # Log audit trail
                self.audit.log_action(
                    user_id=changed_by or user_id,
                    action="CHANGE_PASSWORD",
                    table_name="users",
                    record_id=str(user_id)
                )
                
                logger.info(f"Password changed for user {user_id}")
                return True, "Password changed successfully"
            else:
                return False, "Failed to change password"
                
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            return False, "An error occurred while changing password"
    
    def get_users_by_company(self, company_id: str) -> List[Dict]:
        """Get users by company ID"""
        try:
            query = '''
                SELECT id, username, email, role, created_at, updated_at, 
                       last_login, is_active
                FROM users 
                WHERE company_id = ? AND is_active = 1
                ORDER BY username
            '''
            return self.db.fetch_all(query, (company_id,))
        except Exception as e:
            logger.error(f"Error getting users by company {company_id}: {e}")
            return []
    
    def search_users(self, search_term: str, role: str = None, 
                    company_id: str = None, requester_role: str = None) -> List[Dict]:
        """Search users (admin only)"""
        if requester_role != 'admin':
            return []
        
        return self.user_model.search(search_term, role, company_id)
    
    def get_user_stats(self, requester_role: str = None) -> Dict:
        """Get user statistics (admin only)"""
        if requester_role != 'admin':
            return {}
        
        return self.user_model.get_user_stats()
    
    def _validate_user_input(self, username: str, email: str, 
                           password: str, role: str) -> Tuple[bool, str]:
        """Validate user input data"""
        
        # Validate username
        if not self._validate_username(username):
            return False, "Username must be 3-50 characters, alphanumeric and underscores only"
        
        # Validate email
        if not self._validate_email(email):
            return False, "Invalid email format"
        
        # Validate password
        is_strong, errors = self.security.validate_password_strength(password)
        if not is_strong:
            return False, "; ".join(errors)
        
        # Validate role
        if role not in ['admin', 'user']:
            return False, "Invalid role"
        
        return True, "Valid"
    
    def _validate_username(self, username: str) -> bool:
        """Validate username format"""
        import re
        if not username or len(username) < 3 or len(username) > 50:
            return False
        return re.match(r'^[a-zA-Z0-9_]+$', username) is not None
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None