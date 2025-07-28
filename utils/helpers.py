# utils/helpers.py
"""
Helper functions for the financial system
"""

import re
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def generate_voucher_number(voucher_type: str, year: int = None) -> str:
    """
    Generate voucher number in format: VP-2024-001 or CV-2024-001
    
    Args:
        voucher_type: 'VP' for Voucher Payable, 'CV' for Check Voucher
        year: Year (defaults to current year)
    
    Returns:
        String: Formatted voucher number
    """
    if year is None:
        year = datetime.now().year
    
    try:
        from core.database import DatabaseManager
        
        db_path = current_app.config.get('DATABASE_PATH', 'financial_system.db')
        db_manager = DatabaseManager(db_path)
        
        # Get the highest number for this type and year
        query = '''
            SELECT COALESCE(MAX(
                CAST(SUBSTR(number, LENGTH(?) + 6) AS INTEGER)
            ), 0) as max_num
            FROM ledger 
            WHERE type = ? AND strftime('%Y', date) = ?
        '''
        
        result = db_manager.fetch_one(query, (voucher_type, voucher_type, str(year)))
        next_num = (result['max_num'] if result else 0) + 1
        
        return f"{voucher_type}-{year}-{next_num:03d}"
        
    except Exception as e:
        logger.error(f"Error generating voucher number: {e}")
        # Fallback to simple format
        return f"{voucher_type}-{year}-001"

def format_currency(amount: Union[float, Decimal, str], currency: str = 'USD') -> str:
    """
    Format amount as currency
    
    Args:
        amount: Amount to format
        currency: Currency code (default: USD)
    
    Returns:
        String: Formatted currency
    """
    try:
        if isinstance(amount, str):
            amount = float(amount)
        elif isinstance(amount, Decimal):
            amount = float(amount)
        
        if currency.upper() == 'USD':
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return "0.00"

def parse_currency(currency_string: str) -> float:
    """
    Parse currency string to float
    
    Args:
        currency_string: String like "$1,234.56" or "1234.56"
    
    Returns:
        float: Parsed amount
    """
    try:
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.-]', '', currency_string)
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0

def format_date(date_value: Union[datetime, date, str], format_str: str = '%Y-%m-%d') -> str:
    """
    Format date consistently
    
    Args:
        date_value: Date to format
        format_str: Format string
    
    Returns:
        String: Formatted date
    """
    try:
        if isinstance(date_value, str):
            # Try to parse common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    date_value = datetime.strptime(date_value, fmt)
                    break
                except ValueError:
                    continue
        
        if isinstance(date_value, datetime):
            return date_value.strftime(format_str)
        elif isinstance(date_value, date):
            return date_value.strftime(format_str)
        
        return str(date_value)
    except Exception:
        return ""

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file storage
    
    Args:
        filename: Original filename
    
    Returns:
        String: Sanitized filename
    """
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized

def generate_reference_number() -> str:
    """
    Generate unique reference number
    
    Returns:
        String: Unique reference number
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = str(uuid.uuid4())[:8].upper()
    return f"REF-{timestamp}-{random_part}"

def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email to validate
    
    Returns:
        bool: True if valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """
    Validate phone number (basic)
    
    Args:
        phone: Phone number to validate
    
    Returns:
        bool: True if valid
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    # Check if it's 10-15 digits (common phone number lengths)
    return 10 <= len(digits_only) <= 15

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        String: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def safe_json_dumps(obj: Any, indent: int = None) -> str:
    """
    Safely serialize object to JSON
    
    Args:
        obj: Object to serialize
        indent: JSON indentation
    
    Returns:
        String: JSON string
    """
    try:
        return json.dumps(obj, indent=indent, default=str, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return "{}"

def safe_json_loads(json_string: str) -> Any:
    """
    Safely deserialize JSON string
    
    Args:
        json_string: JSON string to deserialize
    
    Returns:
        Any: Deserialized object or None
    """
    try:
        return json.loads(json_string) if json_string else None
    except Exception as e:
        logger.error(f"JSON deserialization error: {e}")
        return None

def calculate_days_between(start_date: Union[datetime, date, str], 
                          end_date: Union[datetime, date, str]) -> int:
    """
    Calculate days between two dates
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        int: Number of days
    """
    try:
        # Convert to datetime objects if needed
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        delta = end_date - start_date
        return delta.days
    except Exception:
        return 0

def get_financial_year(date_value: Union[datetime, date, str] = None) -> str:
    """
    Get financial year (April to March)
    
    Args:
        date_value: Date to check (defaults to today)
    
    Returns:
        String: Financial year like "2024-25"
    """
    try:
        if date_value is None:
            date_value = datetime.now()
        elif isinstance(date_value, str):
            date_value = datetime.strptime(date_value, '%Y-%m-%d')
        
        if date_value.month >= 4:  # April onwards
            start_year = date_value.year
            end_year = date_value.year + 1
        else:  # January to March
            start_year = date_value.year - 1
            end_year = date_value.year
        
        return f"{start_year}-{str(end_year)[2:]}"
    except Exception:
        return datetime.now().strftime("%Y-%y")

def paginate_results(items: List[Any], page: int = 1, per_page: int = 25) -> Dict:
    """
    Paginate a list of items
    
    Args:
        items: List of items to paginate
        page: Current page number (1-based)
        per_page: Items per page
    
    Returns:
        Dict: Pagination info with items
    """
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    items_on_page = items[start:end]
    
    has_prev = page > 1
    has_next = end < total
    
    return {
        'items': items_on_page,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': page - 1 if has_prev else None,
        'next_num': page + 1 if has_next else None
    }

def calculate_tax(amount: float, tax_rate: float = 0.0) -> Dict[str, float]:
    """
    Calculate tax on amount
    
    Args:
        amount: Base amount
        tax_rate: Tax rate (e.g., 0.18 for 18%)
    
    Returns:
        Dict: Tax calculation details
    """
    tax_amount = amount * tax_rate
    total_amount = amount + tax_amount
    
    return {
        'base_amount': round(amount, 2),
        'tax_rate': tax_rate,
        'tax_amount': round(tax_amount, 2),
        'total_amount': round(total_amount, 2)
    }

def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    Mask sensitive data (like account numbers)
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at end
    
    Returns:
        String: Masked data
    """
    if not data or len(data) <= visible_chars:
        return data
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]

def get_next_working_day(date_value: Union[datetime, date] = None) -> date:
    """
    Get next working day (Monday-Friday)
    
    Args:
        date_value: Starting date (defaults to today)
    
    Returns:
        date: Next working day
    """
    if date_value is None:
        date_value = date.today()
    elif isinstance(date_value, datetime):
        date_value = date_value.date()
    
    # Add days until we get a weekday (0=Monday, 6=Sunday)
    days_to_add = 1
    next_date = date_value
    
    while True:
        next_date = date_value + timedelta(days=days_to_add)
        if next_date.weekday() < 5:  # Monday=0, Friday=4
            break
        days_to_add += 1
    
    return next_date