# services/audit_service.py
"""
Audit Service - System audit logging and tracking
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger('audit')

class AuditService:
    """Audit logging and tracking service"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def log_action(self, user_id: int = None, action: str = None, 
                   table_name: str = None, record_id: str = None,
                   old_values: Dict = None, new_values: Dict = None,
                   ip_address: str = None, user_agent: str = None,
                   details: Dict = None) -> bool:
        """
        Log an audit action
        
        Args:
            user_id: ID of user performing action
            action: Action being performed (e.g., CREATE_USER, UPDATE_VOUCHER)
            table_name: Database table affected
            record_id: ID of record affected
            old_values: Previous values (for updates/deletes)
            new_values: New values (for creates/updates)
            ip_address: User's IP address
            user_agent: User's browser/client info
            details: Additional details about the action
        """
        try:
            query = '''
                INSERT INTO system_logs 
                (user_id, action, table_name, record_id, old_values, new_values, 
                 ip_address, user_agent, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            '''
            
            params = (
                user_id,
                action,
                table_name,
                record_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                ip_address,
                user_agent,
                json.dumps(details) if details else None
            )
            
            success = self.db.execute_query(query, params)
            
            if success:
                # Also log to file
                audit_message = f"User {user_id} performed {action}"
                if table_name:
                    audit_message += f" on {table_name}"
                if record_id:
                    audit_message += f" (ID: {record_id})"
                if ip_address:
                    audit_message += f" from {ip_address}"
                
                logger.info(audit_message)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            return False
    
    def get_audit_trail(self, table_name: str = None, record_id: str = None,
                       user_id: int = None, action: str = None,
                       start_date: str = None, end_date: str = None,
                       limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get audit trail with optional filters
        
        Args:
            table_name: Filter by table name
            record_id: Filter by record ID
            user_id: Filter by user ID
            action: Filter by action type
            start_date: Start date for date range filter
            end_date: End date for date range filter
            limit: Maximum number of records to return
            offset: Number of records to skip
        """
        try:
            # Build dynamic query
            query = '''
                SELECT 
                    sl.id,
                    sl.user_id,
                    sl.action,
                    sl.table_name,
                    sl.record_id,
                    sl.old_values,
                    sl.new_values,
                    sl.ip_address,
                    sl.user_agent,
                    sl.details,
                    sl.timestamp,
                    u.username
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                WHERE 1=1
            '''
            
            params = []
            
            # Add filters
            if table_name:
                query += " AND sl.table_name = ?"
                params.append(table_name)
            
            if record_id:
                query += " AND sl.record_id = ?"
                params.append(record_id)
            
            if user_id:
                query += " AND sl.user_id = ?"
                params.append(user_id)
            
            if action:
                query += " AND sl.action = ?"
                params.append(action)
            
            if start_date:
                query += " AND sl.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND sl.timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY sl.timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            if offset:
                query += " OFFSET ?"
                params.append(offset)
            
            results = self.db.fetch_all(query, tuple(params))
            
            # Parse JSON fields
            audit_records = []
            for record in results:
                audit_record = dict(record)
                
                # Parse JSON fields safely
                try:
                    audit_record['old_values'] = json.loads(record['old_values']) if record['old_values'] else None
                except (json.JSONDecodeError, TypeError):
                    audit_record['old_values'] = None
                
                try:
                    audit_record['new_values'] = json.loads(record['new_values']) if record['new_values'] else None
                except (json.JSONDecodeError, TypeError):
                    audit_record['new_values'] = None
                
                try:
                    audit_record['details'] = json.loads(record['details']) if record['details'] else None
                except (json.JSONDecodeError, TypeError):
                    audit_record['details'] = None
                
                audit_records.append(audit_record)
            
            return audit_records
            
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return []
    
    def get_user_activity_summary(self, user_id: int, days: int = 30) -> Dict:
        """Get activity summary for a specific user"""
        try:
            summary = {}
            
            # Total actions in period
            total_result = self.db.fetch_one('''
                SELECT COUNT(*) as count
                FROM system_logs
                WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
            '''.format(days), (user_id,))
            
            summary['total_actions'] = total_result['count'] if total_result else 0
            
            # Actions by type
            actions_result = self.db.fetch_all('''
                SELECT action, COUNT(*) as count
                FROM system_logs
                WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
                GROUP BY action
                ORDER BY count DESC
            '''.format(days), (user_id,))
            
            summary['actions_by_type'] = {row['action']: row['count'] for row in actions_result}
            
            # Daily activity
            daily_result = self.db.fetch_all('''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as count
                FROM system_logs
                WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            '''.format(days), (user_id,))
            
            summary['daily_activity'] = {row['date']: row['count'] for row in daily_result}
            
            # Most recent login
            login_result = self.db.fetch_one('''
                SELECT timestamp
                FROM system_logs
                WHERE user_id = ? AND action = 'LOGIN_SUCCESS'
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (user_id,))
            
            summary['last_login'] = login_result['timestamp'] if login_result else None
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            return {}
    
    def get_system_activity_summary(self, days: int = 30) -> Dict:
        """Get system-wide activity summary (admin only)"""
        try:
            summary = {}
            
            # Total system actions
            total_result = self.db.fetch_one('''
                SELECT COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= datetime('now', '-{} days')
            '''.format(days))
            
            summary['total_actions'] = total_result['count'] if total_result else 0
            
            # Most active users
            users_result = self.db.fetch_all('''
                SELECT 
                    sl.user_id,
                    u.username,
                    COUNT(*) as action_count
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                WHERE sl.timestamp >= datetime('now', '-{} days')
                GROUP BY sl.user_id, u.username
                ORDER BY action_count DESC
                LIMIT 10
            '''.format(days))
            
            summary['most_active_users'] = [
                {
                    'user_id': row['user_id'],
                    'username': row['username'] or 'Unknown',
                    'action_count': row['action_count']
                }
                for row in users_result
            ]
            
            # Actions by type
            actions_result = self.db.fetch_all('''
                SELECT action, COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY action
                ORDER BY count DESC
            '''.format(days))
            
            summary['actions_by_type'] = {row['action']: row['count'] for row in actions_result}
            
            # Hourly distribution
            hourly_result = self.db.fetch_all('''
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            '''.format(days))
            
            summary['hourly_distribution'] = {row['hour']: row['count'] for row in hourly_result}
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting system activity summary: {e}")
            return {}
    
    def search_audit_logs(self, search_term: str, limit: int = 100) -> List[Dict]:
        """Search audit logs by various criteria"""
        try:
            query = '''
                SELECT 
                    sl.id,
                    sl.user_id,
                    sl.action,
                    sl.table_name,
                    sl.record_id,
                    sl.timestamp,
                    u.username
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                WHERE 
                    sl.action LIKE ? OR
                    sl.table_name LIKE ? OR
                    sl.record_id LIKE ? OR
                    u.username LIKE ? OR
                    sl.ip_address LIKE ?
                ORDER BY sl.timestamp DESC
                LIMIT ?
            '''
            
            search_pattern = f'%{search_term}%'
            params = (search_pattern, search_pattern, search_pattern, 
                     search_pattern, search_pattern, limit)
            
            return self.db.fetch_all(query, params)
            
        except Exception as e:
            logger.error(f"Error searching audit logs: {e}")
            return []
    
    def create_audit_table(self) -> bool:
        """Create the system_logs table if it doesn't exist"""
        try:
            query = '''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action VARCHAR(100) NOT NULL,
                    table_name VARCHAR(50),
                    record_id VARCHAR(50),
                    old_values TEXT,
                    new_values TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            '''
            
            success = self.db.execute_query(query)
            if success:
                # Create indexes for better performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_system_logs_action ON system_logs(action)",
                    "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_system_logs_table_name ON system_logs(table_name)"
                ]
                
                for index_query in indexes:
                    self.db.execute_query(index_query)
                
                logger.info("Audit table and indexes created successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating audit table: {e}")
            return False
    
    def cleanup_old_logs(self, days_to_keep: int = 365) -> int:
        """Clean up old audit logs to manage database size"""
        try:
            # Count records to be deleted
            count_result = self.db.fetch_one('''
                SELECT COUNT(*) as count
                FROM system_logs
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days_to_keep))
            
            records_to_delete = count_result['count'] if count_result else 0
            
            if records_to_delete > 0:
                # Delete old records
                delete_query = '''
                    DELETE FROM system_logs
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days_to_keep)
                
                success = self.db.execute_query(delete_query)
                
                if success:
                    logger.info(f"Deleted {records_to_delete} old audit log records")
                    
                    # Log the cleanup action
                    self.log_action(
                        action="CLEANUP_AUDIT_LOGS",
                        details={'records_deleted': records_to_delete, 'days_kept': days_to_keep}
                    )
                    
                    return records_to_delete
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up old audit logs: {e}")
            return 0
    
    def export_audit_logs(self, filters: Dict = None, format: str = 'json') -> str:
        """Export audit logs to various formats"""
        try:
            # Get audit trail with filters
            audit_logs = self.get_audit_trail(
                table_name=filters.get('table_name') if filters else None,
                user_id=filters.get('user_id') if filters else None,
                action=filters.get('action') if filters else None,
                start_date=filters.get('start_date') if filters else None,
                end_date=filters.get('end_date') if filters else None,
                limit=filters.get('limit', 10000) if filters else 10000
            )
            
            if format.lower() == 'json':
                return json.dumps(audit_logs, indent=2, default=str)
            elif format.lower() == 'csv':
                return self._export_to_csv(audit_logs)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting audit logs: {e}")
            return ""
    
    def _export_to_csv(self, audit_logs: List[Dict]) -> str:
        """Convert audit logs to CSV format"""
        import csv
        import io
        
        if not audit_logs:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'id', 'timestamp', 'username', 'action', 'table_name', 
            'record_id', 'ip_address', 'details'
        ])
        
        writer.writeheader()
        for log in audit_logs:
            # Flatten the log entry for CSV
            csv_row = {
                'id': log.get('id'),
                'timestamp': log.get('timestamp'),
                'username': log.get('username'),
                'action': log.get('action'),
                'table_name': log.get('table_name'),
                'record_id': log.get('record_id'),
                'ip_address': log.get('ip_address'),
                'details': json.dumps(log.get('details')) if log.get('details') else ''
            }
            writer.writerow(csv_row)
        
        return output.getvalue()
    
    def get_audit_statistics(self) -> Dict:
        """Get statistics about audit logs"""
        try:
            stats = {}
            
            # Total audit records
            total_result = self.db.fetch_one('SELECT COUNT(*) as count FROM system_logs')
            stats['total_records'] = total_result['count'] if total_result else 0
            
            # Records by action type
            action_stats = self.db.fetch_all('''
                SELECT action, COUNT(*) as count
                FROM system_logs
                GROUP BY action
                ORDER BY count DESC
            ''')
            stats['by_action'] = {row['action']: row['count'] for row in action_stats}
            
            # Records by table
            table_stats = self.db.fetch_all('''
                SELECT table_name, COUNT(*) as count
                FROM system_logs
                WHERE table_name IS NOT NULL
                GROUP BY table_name
                ORDER BY count DESC
            ''')
            stats['by_table'] = {row['table_name']: row['count'] for row in table_stats}
            
            # Date range
            date_range = self.db.fetch_one('''
                SELECT 
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest
                FROM system_logs
            ''')
            
            if date_range:
                stats['date_range'] = {
                    'earliest': date_range['earliest'],
                    'latest': date_range['latest']
                }
            
            # Recent activity (last 24 hours)
            recent_result = self.db.fetch_one('''
                SELECT COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= datetime('now', '-24 hours')
            ''')
            stats['recent_activity'] = recent_result['count'] if recent_result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return {}