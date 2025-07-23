# services/dashboard_service.py
"""
Dashboard Service - Business logic for dashboard analytics and statistics
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    """Dashboard analytics and statistics service"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_dashboard_stats(self, user_id: int, user_role: str, 
                           company_id: str = None) -> Dict:
        """Get dashboard statistics based on user role and permissions"""
        try:
            stats = {
                'user_stats': {},
                'voucher_stats': {},
                'financial_summary': {},
                'system_stats': {}
            }
            
            if user_role == 'admin':
                # Admin gets system-wide statistics
                stats['user_stats'] = self._get_user_statistics()
                stats['voucher_stats'] = self._get_voucher_statistics()
                stats['financial_summary'] = self._get_financial_summary()
                stats['system_stats'] = self._get_system_statistics()
            else:
                # Regular users get limited statistics
                stats['voucher_stats'] = self._get_user_voucher_statistics(user_id, company_id)
                stats['financial_summary'] = self._get_user_financial_summary(user_id, company_id)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {}
    
    def get_recent_activities(self, user_id: int, user_role: str, 
                             limit: int = 10) -> List[Dict]:
        """Get recent activities based on user permissions"""
        try:
            if user_role == 'admin':
                # Admin sees all activities
                return self._get_system_activities(limit)
            else:
                # Regular users see only their activities
                return self._get_user_activities(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}")
            return []
    
    def _get_user_statistics(self) -> Dict:
        """Get user-related statistics (admin only)"""
        try:
            stats = {}
            
            # Total active users
            result = self.db.fetch_one('''
                SELECT COUNT(*) as count 
                FROM users 
                WHERE is_active = 1
            ''')
            stats['total_users'] = result['count'] if result else 0
            
            # Users by role
            result = self.db.fetch_all('''
                SELECT role, COUNT(*) as count 
                FROM users 
                WHERE is_active = 1 
                GROUP BY role
            ''')
            stats['by_role'] = {row['role']: row['count'] for row in result}
            
            # Recent registrations (last 30 days)
            result = self.db.fetch_one('''
                SELECT COUNT(*) as count 
                FROM users 
                WHERE created_at >= datetime('now', '-30 days') AND is_active = 1
            ''')
            stats['recent_registrations'] = result['count'] if result else 0
            
            # Active users (logged in last 7 days)
            result = self.db.fetch_one('''
                SELECT COUNT(*) as count 
                FROM users 
                WHERE last_login >= datetime('now', '-7 days') AND is_active = 1
            ''')
            stats['active_users'] = result['count'] if result else 0
            
            return stats
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    def _get_voucher_statistics(self) -> Dict:
        """Get voucher-related statistics (admin only)"""
        try:
            stats = {}
            
            # Vouchers Payable statistics
            vp_stats = self.db.fetch_one('''
                SELECT 
                    COUNT(*) as total_count,
                    SUM(amount_to_pay) as total_amount,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                    SUM(CASE WHEN status = 'pending' THEN amount_to_pay ELSE 0 END) as pending_amount
                FROM vouchers_payable
            ''')
            
            if vp_stats:
                stats['vouchers_payable'] = {
                    'total_count': vp_stats['total_count'] or 0,
                    'total_amount': float(vp_stats['total_amount'] or 0),
                    'pending_count': vp_stats['pending_count'] or 0,
                    'pending_amount': float(vp_stats['pending_amount'] or 0)
                }
            else:
                stats['vouchers_payable'] = {
                    'total_count': 0, 'total_amount': 0,
                    'pending_count': 0, 'pending_amount': 0
                }
            
            # Check Vouchers statistics
            cv_stats = self.db.fetch_one('''
                SELECT 
                    COUNT(*) as total_count,
                    SUM(amount_to_pay) as total_amount
                FROM check_vouchers
            ''')
            
            if cv_stats:
                stats['check_vouchers'] = {
                    'total_count': cv_stats['total_count'] or 0,
                    'total_amount': float(cv_stats['total_amount'] or 0)
                }
            else:
                stats['check_vouchers'] = {'total_count': 0, 'total_amount': 0}
            
            return stats
        except Exception as e:
            logger.error(f"Error getting voucher statistics: {e}")
            return {}
    
    def _get_financial_summary(self) -> Dict:
        """Get financial summary (admin only)"""
        try:
            summary = {}
            
            # Monthly financial trends
            monthly_data = self.db.fetch_all('''
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    SUM(amount_to_pay) as total_amount,
                    COUNT(*) as voucher_count
                FROM vouchers_payable
                WHERE created_at >= datetime('now', '-12 months')
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month
            ''')
            
            summary['monthly_trends'] = [
                {
                    'month': row['month'],
                    'total_amount': float(row['total_amount'] or 0),
                    'voucher_count': row['voucher_count']
                }
                for row in monthly_data
            ]
            
            # Top companies by transaction volume
            top_companies = self.db.fetch_all('''
                SELECT 
                    company_id,
                    company_name,
                    COUNT(*) as voucher_count,
                    SUM(amount_to_pay) as total_amount
                FROM vouchers_payable
                GROUP BY company_id, company_name
                ORDER BY total_amount DESC
                LIMIT 5
            ''')
            
            summary['top_companies'] = [
                {
                    'company_id': row['company_id'],
                    'company_name': row['company_name'],
                    'voucher_count': row['voucher_count'],
                    'total_amount': float(row['total_amount'] or 0)
                }
                for row in top_companies
            ]
            
            return summary
        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            return {}
    
    def _get_system_statistics(self) -> Dict:
        """Get system-related statistics (admin only)"""
        try:
            stats = {}
            
            # Database size and record counts
            tables_info = self.db.fetch_all('''
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=main.name) as exists
                FROM (
                    SELECT 'users' as name UNION ALL
                    SELECT 'companies' UNION ALL
                    SELECT 'vouchers_payable' UNION ALL
                    SELECT 'check_vouchers' UNION ALL
                    SELECT 'system_logs'
                ) main
            ''')
            
            record_counts = {}
            for table in ['users', 'companies', 'vouchers_payable', 'check_vouchers', 'system_logs']:
                try:
                    result = self.db.fetch_one(f'SELECT COUNT(*) as count FROM {table}')
                    record_counts[table] = result['count'] if result else 0
                except:
                    record_counts[table] = 0
            
            stats['record_counts'] = record_counts
            
            # Recent system activities
            recent_logs = self.db.fetch_one('''
                SELECT COUNT(*) as count 
                FROM system_logs 
                WHERE timestamp >= datetime('now', '-24 hours')
            ''')
            stats['recent_activities'] = recent_logs['count'] if recent_logs else 0
            
            return stats
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}
    
    def _get_user_voucher_statistics(self, user_id: int, company_id: str = None) -> Dict:
        """Get voucher statistics for a specific user"""
        try:
            stats = {}
            
            # User's vouchers
            where_clause = "WHERE created_by = ?"
            params = [user_id]
            
            if company_id:
                where_clause += " AND company_id = ?"
                params.append(company_id)
            
            vp_stats = self.db.fetch_one(f'''
                SELECT 
                    COUNT(*) as total_count,
                    SUM(amount_to_pay) as total_amount,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count
                FROM vouchers_payable
                {where_clause}
            ''', tuple(params))
            
            if vp_stats:
                stats['my_vouchers'] = {
                    'total_count': vp_stats['total_count'] or 0,
                    'total_amount': float(vp_stats['total_amount'] or 0),
                    'pending_count': vp_stats['pending_count'] or 0
                }
            else:
                stats['my_vouchers'] = {'total_count': 0, 'total_amount': 0, 'pending_count': 0}
            
            return stats
        except Exception as e:
            logger.error(f"Error getting user voucher statistics: {e}")
            return {}
    
    def _get_user_financial_summary(self, user_id: int, company_id: str = None) -> Dict:
        """Get financial summary for a specific user"""
        try:
            summary = {}
            
            # Monthly summary for user
            where_clause = "WHERE created_by = ?"
            params = [user_id]
            
            if company_id:
                where_clause += " AND company_id = ?"
                params.append(company_id)
            
            monthly_data = self.db.fetch_all(f'''
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    SUM(amount_to_pay) as total_amount,
                    COUNT(*) as voucher_count
                FROM vouchers_payable
                {where_clause} AND created_at >= datetime('now', '-6 months')
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month
            ''', tuple(params))
            
            summary['monthly_summary'] = [
                {
                    'month': row['month'],
                    'total_amount': float(row['total_amount'] or 0),
                    'voucher_count': row['voucher_count']
                }
                for row in monthly_data
            ]
            
            return summary
        except Exception as e:
            logger.error(f"Error getting user financial summary: {e}")
            return {}
    
    def _get_system_activities(self, limit: int) -> List[Dict]:
        """Get recent system activities (admin only)"""
        try:
            activities = self.db.fetch_all('''
                SELECT 
                    sl.action,
                    sl.table_name,
                    sl.timestamp,
                    sl.ip_address,
                    u.username
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                ORDER BY sl.timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            return [
                {
                    'action': activity['action'],
                    'table_name': activity['table_name'],
                    'timestamp': activity['timestamp'],
                    'ip_address': activity['ip_address'],
                    'username': activity['username'] or 'System'
                }
                for activity in activities
            ]
        except Exception as e:
            logger.error(f"Error getting system activities: {e}")
            return []
    
    def _get_user_activities(self, user_id: int, limit: int) -> List[Dict]:
        """Get recent activities for a specific user"""
        try:
            activities = self.db.fetch_all('''
                SELECT 
                    action,
                    table_name,
                    timestamp,
                    ip_address
                FROM system_logs
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_id, limit))
            
            return [
                {
                    'action': activity['action'],
                    'table_name': activity['table_name'],
                    'timestamp': activity['timestamp'],
                    'ip_address': activity['ip_address']
                }
                for activity in activities
            ]
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []
    
    def get_chart_data(self, chart_type: str, user_id: int = None, 
                      user_role: str = None) -> Dict:
        """Get data for dashboard charts"""
        try:
            if chart_type == 'monthly_vouchers':
                return self._get_monthly_vouchers_chart_data(user_id, user_role)
            elif chart_type == 'voucher_status':
                return self._get_voucher_status_chart_data(user_id, user_role)
            elif chart_type == 'company_breakdown':
                return self._get_company_breakdown_chart_data(user_id, user_role)
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting chart data for {chart_type}: {e}")
            return {}
    
    def _get_monthly_vouchers_chart_data(self, user_id: int = None, 
                                        user_role: str = None) -> Dict:
        """Get monthly vouchers data for charts"""
        try:
            if user_role == 'admin':
                # Admin sees all data
                data = self.db.fetch_all('''
                    SELECT 
                        strftime('%m', created_at) as month,
                        strftime('%Y', created_at) as year,
                        COUNT(*) as count,
                        SUM(amount_to_pay) as amount
                    FROM vouchers_payable
                    WHERE created_at >= datetime('now', '-12 months')
                    GROUP BY strftime('%Y-%m', created_at)
                    ORDER BY year, month
                ''')
            else:
                # Users see only their data
                data = self.db.fetch_all('''
                    SELECT 
                        strftime('%m', created_at) as month,
                        strftime('%Y', created_at) as year,
                        COUNT(*) as count,
                        SUM(amount_to_pay) as amount
                    FROM vouchers_payable
                    WHERE created_by = ? AND created_at >= datetime('now', '-12 months')
                    GROUP BY strftime('%Y-%m', created_at)
                    ORDER BY year, month
                ''', (user_id,))
            
            return {
                'labels': [f"{row['year']}-{row['month'].zfill(2)}" for row in data],
                'voucher_counts': [row['count'] for row in data],
                'amounts': [float(row['amount'] or 0) for row in data]
            }
        except Exception as e:
            logger.error(f"Error getting monthly vouchers chart data: {e}")
            return {'labels': [], 'voucher_counts': [], 'amounts': []}
    
    def _get_voucher_status_chart_data(self, user_id: int = None, 
                                      user_role: str = None) -> Dict:
        """Get voucher status distribution for pie charts"""
        try:
            if user_role == 'admin':
                data = self.db.fetch_all('''
                    SELECT status, COUNT(*) as count
                    FROM vouchers_payable
                    GROUP BY status
                ''')
            else:
                data = self.db.fetch_all('''
                    SELECT status, COUNT(*) as count
                    FROM vouchers_payable
                    WHERE created_by = ?
                    GROUP BY status
                ''', (user_id,))
            
            return {
                'labels': [row['status'] for row in data],
                'counts': [row['count'] for row in data]
            }
        except Exception as e:
            logger.error(f"Error getting voucher status chart data: {e}")
            return {'labels': [], 'counts': []}
    
    def _get_company_breakdown_chart_data(self, user_id: int = None, 
                                         user_role: str = None) -> Dict:
        """Get company breakdown for charts"""
        try:
            if user_role != 'admin':
                return {'labels': [], 'amounts': []}
            
            data = self.db.fetch_all('''
                SELECT 
                    company_name,
                    SUM(amount_to_pay) as total_amount
                FROM vouchers_payable
                GROUP BY company_id, company_name
                ORDER BY total_amount DESC
                LIMIT 10
            ''')
            
            return {
                'labels': [row['company_name'] for row in data],
                'amounts': [float(row['total_amount'] or 0) for row in data]
            }
        except Exception as e:
            logger.error(f"Error getting company breakdown chart data: {e}")
            return {'labels': [], 'amounts': []}