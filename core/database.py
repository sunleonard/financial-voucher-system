import sqlite3
import json
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Centralized database management"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> bool:
        """Execute a query that doesn't return results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return False
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch a single row"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            return None
    
    def fetch_all(self, query: str, params: tuple = None) -> list:
        """Fetch multiple rows"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all failed: {e}")
            return []
    
    def init_database(self):
        """Initialize database schema"""
        logger.info(f"Initializing database at {self.db_path}")
        
        # Import schema creation functions
        from migrations.init_db import create_schema, insert_default_data
        
        create_schema(self.db_path)
        insert_default_data(self.db_path)
        
        logger.info("Database initialization completed")
