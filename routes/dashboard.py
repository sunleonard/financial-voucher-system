# routes/dashboard.py
"""
Dashboard Routes - Main dashboard and analytics
"""

from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
from utils.decorators import login_required, audit_action
from services.user_service import UserService
from services.dashboard_service import DashboardService
import logging

logger = logging.getLogger(__name__)

def create_dashboard_blueprint(db_manager):
    """Create and configure dashboard blueprint"""
    
    dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
    user_service = UserService(db_manager)
    dashboard_service = DashboardService(db_manager)
    
    @dashboard_bp.route('/')
    @login_required
    @audit_action("VIEW_DASHBOARD")
    def index():
        """Main dashboard page"""
        try:
            user = user_service.get_user_by_id(session.get('user_id'))
            if not user:
                return redirect(url_for('auth.logout'))
            
            # Get dashboard statistics
            stats = dashboard_service.get_dashboard_stats(
                user_id=session.get('user_id'),
                user_role=session.get('role'),
                company_id=session.get('company_id')
            )
            
            # Get recent activities
            recent_activities = dashboard_service.get_recent_activities(
                user_id=session.get('user_id'),
                user_role=session.get('role'),
                limit=10
            )
            
            return render_template('dashboard/index.html', 
                                 user=user,
                                 stats=stats,
                                 recent_activities=recent_activities)
        except Exception as e:
            logger.error(f"Error loading dashboard: {e}")
            return render_template('dashboard/error.html', 
                                 error="Failed to load dashboard")
    
    @dashboard_bp.route('/api/stats')
    @login_required
    def api_stats():
        """API endpoint for dashboard statistics"""
        try:
            stats = dashboard_service.get_dashboard_stats(
                user_id=session.get('user_id'),
                user_role=session.get('role'),
                company_id=session.get('company_id')
            )
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return jsonify({'error': 'Failed to get statistics'}), 500
    
    @dashboard_bp.route('/api/activities')
    @login_required
    def api_activities():
        """API endpoint for recent activities"""
        try:
            limit = request.args.get('limit', 10, type=int)
            activities = dashboard_service.get_recent_activities(
                user_id=session.get('user_id'),
                user_role=session.get('role'),
                limit=limit
            )
            return jsonify(activities)
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}")
            return jsonify({'error': 'Failed to get activities'}), 500
    
    return dashboard_bp