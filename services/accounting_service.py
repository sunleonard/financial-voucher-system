# services/accounting_service.py
"""
Accounting Service - Complete Transaction Management
Handles VP (Vouchers Payable) and CV (Check Vouchers) with proper double-entry accounting
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime, date
import logging
from decimal import Decimal, ROUND_HALF_UP

from models.ledger import Ledger
from models.ledger_credit_debit import LedgerCreditDebit
from models.ledger_subcodes import LedgerSubcodes
from models.account_definition import AccountDefinition
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

class AccountingService:
    """Comprehensive accounting service for ledger management"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.ledger = Ledger(db_manager)
        self.credit_debit = LedgerCreditDebit(db_manager)
        self.subcodes = LedgerSubcodes(db_manager)
        self.accounts = AccountDefinition(db_manager)
        self.audit = AuditService(db_manager)
    
    def create_voucher_payable(self, transaction_date: date, payee_code: str, 
                              total_amount: float, description: str = None,
                              due_date: date = None, credit_debit_lines: List[Dict] = None,
                              subsidiary_lines: List[Dict] = None, 
                              created_by: int = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a complete Voucher Payable transaction
        
        Args:
            transaction_date: Date of the transaction
            payee_code: Account code of the payee
            total_amount: Total amount of the voucher
            description: Description of the transaction
            due_date: When payment is due
            credit_debit_lines: List of debit/credit entries
            subsidiary_lines: List of subsidiary breakdowns
            created_by: User ID creating the transaction
            
        Returns:
            (success, message, voucher_number)
        """
        try:
            # Validate payee exists
            payee_account = self.accounts.get_by_code(payee_code)
            if not payee_account:
                return False, f"Payee account {payee_code} not found", None
            
            # Round amount to 2 decimal places
            total_amount = float(Decimal(str(total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            # Generate VP number
            vp_number = self.ledger.generate_number("VP", transaction_date.year)
            
            # Validate credit/debit lines balance
            if credit_debit_lines:
                if not self._validate_credit_debit_balance(credit_debit_lines, total_amount):
                    return False, "Credit/debit lines do not balance with total amount", None
            
            # Start transaction
            with self.db.get_connection() as conn:
                conn.execute('BEGIN')
                
                try:
                    # Create main ledger entry
                    ledger_id = self.ledger.create(
                        ledger_type="VP",
                        transaction_date=transaction_date,
                        payee_code=payee_code,
                        payee=payee_account['acct_description'],
                        total_amount=total_amount,
                        description=description,
                        due_date=due_date,
                        created_by=created_by,
                        number=vp_number
                    )
                    
                    if not ledger_id:
                        conn.rollback()
                        return False, "Failed to create ledger entry", None
                    
                    # Create credit/debit entries
                    if credit_debit_lines:
                        cd_entries = []
                        for line in credit_debit_lines:
                            cd_entries.append({
                                'type': 'VP',
                                'number': vp_number,
                                'date': transaction_date,
                                'acct_code': line['acct_code'],
                                'acct_description': line['acct_description'],
                                'amount': float(Decimal(str(line['amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                                'acct_type': line['acct_type']
                            })
                        
                        if not self.credit_debit.create_multiple(cd_entries):
                            conn.rollback()
                            return False, "Failed to create credit/debit entries", None
                    else:
                        # Create default entries: Debit Expense, Credit Accounts Payable
                        default_entries = [
                            {
                                'type': 'VP',
                                'number': vp_number,
                                'date': transaction_date,
                                'acct_code': '5000',  # Default expense account
                                'acct_description': 'General Expense',
                                'amount': total_amount,
                                'acct_type': 'D'
                            },
                            {
                                'type': 'VP',
                                'number': vp_number,
                                'date': transaction_date,
                                'acct_code': '2000',  # Accounts Payable
                                'acct_description': 'Accounts Payable',
                                'amount': total_amount,
                                'acct_type': 'C'
                            }
                        ]
                        
                        if not self.credit_debit.create_multiple(default_entries):
                            conn.rollback()
                            return False, "Failed to create default credit/debit entries", None
                    
                    # Create subsidiary entries if provided
                    if subsidiary_lines:
                        sub_entries = []
                        for line in subsidiary_lines:
                            sub_entries.append({
                                'type': 'VP',
                                'number': vp_number,
                                'date': transaction_date,
                                'acct_code': line['acct_code'],
                                'acct_description': line['acct_description'],
                                'subsidiary_code': line['subsidiary_code'],
                                'subsidiary_description': line['subsidiary_description'],
                                'amount': float(Decimal(str(line['amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                            })
                        
                        if not self.subcodes.create_multiple(sub_entries):
                            conn.rollback()
                            return False, "Failed to create subsidiary entries", None
                    
                    conn.commit()
                    
                    # Log audit trail
                    self.audit.log_action(
                        user_id=created_by,
                        action="CREATE_VOUCHER_PAYABLE",
                        table_name="ledger",
                        record_id=vp_number,
                        new_values={
                            'type': 'VP',
                            'number': vp_number,
                            'payee_code': payee_code,
                            'total_amount': total_amount,
                            'description': description
                        }
                    )
                    
                    logger.info(f"Voucher Payable created: {vp_number} - {payee_account['acct_description']} - ${total_amount}")
                    return True, "Voucher Payable created successfully", vp_number
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
        except Exception as e:
            logger.error(f"Error creating Voucher Payable: {e}")
            return False, f"Error creating Voucher Payable: {str(e)}", None
    
    def create_check_voucher(self, transaction_date: date, payee_code: str,
                           total_amount: float, vp_number: str = None,
                           check_number: str = None, bank_account: str = None,
                           description: str = None, credit_debit_lines: List[Dict] = None,
                           subsidiary_lines: List[Dict] = None,
                           created_by: int = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a complete Check Voucher transaction
        
        Args:
            transaction_date: Date of the check
            payee_code: Account code of the payee
            total_amount: Total amount of the check
            vp_number: Related VP number (optional)
            check_number: Physical check number
            bank_account: Bank account used
            description: Description of the payment
            credit_debit_lines: List of debit/credit entries
            subsidiary_lines: List of subsidiary breakdowns
            created_by: User ID creating the transaction
            
        Returns:
            (success, message, check_voucher_number)
        """
        try:
            # Validate payee exists
            payee_account = self.accounts.get_by_code(payee_code)
            if not payee_account:
                return False, f"Payee account {payee_code} not found", None
            
            # Round amount to 2 decimal places
            total_amount = float(Decimal(str(total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            # Generate CV number
            cv_number = self.ledger.generate_number("CV", transaction_date.year)
            
            # Validate VP number exists if provided
            if vp_number:
                vp_entry = self.ledger.get_by_number(vp_number)
                if not vp_entry:
                    return False, f"Voucher Payable {vp_number} not found", None
                if vp_entry['type'] != 'VP':
                    return False, f"{vp_number} is not a Voucher Payable", None
            
            # Validate credit/debit lines balance
            if credit_debit_lines:
                if not self._validate_credit_debit_balance(credit_debit_lines, total_amount):
                    return False, "Credit/debit lines do not balance with total amount", None
            
            # Build description
            full_description = description or f"Check payment to {payee_account['acct_description']}"
            if check_number:
                full_description += f" - Check #{check_number}"
            if vp_number:
                full_description += f" - Payment for {vp_number}"
            
            # Start transaction
            with self.db.get_connection() as conn:
                conn.execute('BEGIN')
                
                try:
                    # Create main ledger entry
                    ledger_id = self.ledger.create(
                        ledger_type="CV",
                        transaction_date=transaction_date,
                        payee_code=payee_code,
                        payee=payee_account['acct_description'],
                        total_amount=total_amount,
                        description=full_description,
                        created_by=created_by,
                        number=cv_number
                    )
                    
                    if not ledger_id:
                        conn.rollback()
                        return False, "Failed to create ledger entry", None
                    
                    # Create credit/debit entries
                    if credit_debit_lines:
                        cd_entries = []
                        for line in credit_debit_lines:
                            cd_entries.append({
                                'type': 'CV',
                                'number': cv_number,
                                'date': transaction_date,
                                'acct_code': line['acct_code'],
                                'acct_description': line['acct_description'],
                                'amount': float(Decimal(str(line['amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                                'acct_type': line['acct_type']
                            })
                        
                        if not self.credit_debit.create_multiple(cd_entries):
                            conn.rollback()
                            return False, "Failed to create credit/debit entries", None
                    else:
                        # Create default entries: Debit A/P, Credit Cash/Bank
                        bank_acct_code = bank_account or '1010'  # Default to operating account
                        bank_acct_desc = f"Bank - {bank_account}" if bank_account else "Bank - Operating Account"
                        
                        default_entries = [
                            {
                                'type': 'CV',
                                'number': cv_number,
                                'date': transaction_date,
                                'acct_code': '2000',  # Accounts Payable
                                'acct_description': 'Accounts Payable',
                                'amount': total_amount,
                                'acct_type': 'D'
                            },
                            {
                                'type': 'CV',
                                'number': cv_number,
                                'date': transaction_date,
                                'acct_code': bank_acct_code,
                                'acct_description': bank_acct_desc,
                                'amount': total_amount,
                                'acct_type': 'C'
                            }
                        ]
                        
                        if not self.credit_debit.create_multiple(default_entries):
                            conn.rollback()
                            return False, "Failed to create default credit/debit entries", None
                    
                    # Create subsidiary entries if provided
                    if subsidiary_lines:
                        sub_entries = []
                        for line in subsidiary_lines:
                            sub_entries.append({
                                'type': 'CV',
                                'number': cv_number,
                                'date': transaction_date,
                                'acct_code': line['acct_code'],
                                'acct_description': line['acct_description'],
                                'subsidiary_code': line['subsidiary_code'],
                                'subsidiary_description': line['subsidiary_description'],
                                'amount': float(Decimal(str(line['amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                            })
                        
                        if not self.subcodes.create_multiple(sub_entries):
                            conn.rollback()
                            return False, "Failed to create subsidiary entries", None
                    
                    conn.commit()
                    
                    # Log audit trail
                    self.audit.log_action(
                        user_id=created_by,
                        action="CREATE_CHECK_VOUCHER",
                        table_name="ledger",
                        record_id=cv_number,
                        new_values={
                            'type': 'CV',
                            'number': cv_number,
                            'payee_code': payee_code,
                            'total_amount': total_amount,
                            'check_number': check_number,
                            'vp_number': vp_number
                        }
                    )
                    
                    logger.info(f"Check Voucher created: {cv_number} - {payee_account['acct_description']} - ${total_amount}")
                    return True, "Check Voucher created successfully", cv_number
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                    
        except Exception as e:
            logger.error(f"Error creating Check Voucher: {e}")
            return False, f"Error creating Check Voucher: {str(e)}", None
    
    def get_transaction(self, number: str) -> Optional[Dict]:
        """Get complete transaction details including all related entries"""
        try:
            # Get main ledger entry
            ledger_entry = self.ledger.get_by_number(number)
            if not ledger_entry:
                return None
            
            # Get credit/debit entries
            cd_entries = self.credit_debit.get_by_number(number)
            
            # Get subsidiary entries
            sub_entries = self.subcodes.get_by_number(number)
            
            # Validate balance
            balance_check = self.credit_debit.validate_entry_balance(number)
            
            return {
                'ledger': ledger_entry,
                'credit_debit_entries': cd_entries,
                'subsidiary_entries': sub_entries,
                'balance_check': balance_check,
                'is_balanced': balance_check['balanced']
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction {number}: {e}")
            return None
    
    def void_transaction(self, number: str, voided_by: int = None, 
                        reason: str = None) -> Tuple[bool, str]:
        """Void a transaction (mark as void, don't delete)"""
        try:
            # Get transaction
            transaction = self.get_transaction(number)
            if not transaction:
                return False, "Transaction not found"
            
            # Check if already voided
            if transaction['ledger']['status'] == 'void':
                return False, "Transaction already voided"
            
            # Void the main ledger entry
            ledger_entry = transaction['ledger']
            success = self.ledger.void(ledger_entry['id'])
            
            if success:
                # Log audit trail
                self.audit.log_action(
                    user_id=voided_by,
                    action="VOID_TRANSACTION",
                    table_name="ledger",
                    record_id=number,
                    old_values={'status': ledger_entry['status']},
                    new_values={'status': 'void', 'void_reason': reason},
                    details={'reason': reason}
                )
                
                logger.info(f"Transaction voided: {number} by user {voided_by}")
                return True, "Transaction voided successfully"
            else:
                return False, "Failed to void transaction"
                
        except Exception as e:
            logger.error(f"Error voiding transaction {number}: {e}")
            return False, f"Error voiding transaction: {str(e)}"
    
    def get_account_ledger(self, acct_code: str, start_date: date = None, 
                          end_date: date = None, include_balance: bool = True) -> Dict:
        """Get account ledger with running balance"""
        try:
            # Get account info
            account = self.accounts.get_by_code(acct_code)
            if not account:
                return {'error': f'Account {acct_code} not found'}
            
            # Get all transactions for this account
            transactions = self.credit_debit.get_by_account(acct_code, start_date, end_date)
            
            # Calculate running balance if requested
            running_balance = 0
            if include_balance:
                for transaction in transactions:
                    if transaction['acct_type'] == 'D':
                        running_balance += transaction['amount']
                    else:
                        running_balance -= transaction['amount']
                    transaction['running_balance'] = running_balance
            
            # Get account balance
            balance_info = self.credit_debit.get_account_balance(acct_code, end_date)
            
            return {
                'account': account,
                'transactions': transactions,
                'balance': balance_info,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date or date.today()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting account ledger for {acct_code}: {e}")
            return {'error': f'Error getting account ledger: {str(e)}'}
    
    def get_trial_balance(self, as_of_date: date = None) -> Dict:
        """Get trial balance report"""
        try:
            trial_balance = self.credit_debit.get_trial_balance(as_of_date)
            
            # Calculate totals
            total_debits = sum(entry['total_debits'] for entry in trial_balance)
            total_credits = sum(entry['total_credits'] for entry in trial_balance)
            
            return {
                'trial_balance': trial_balance,
                'totals': {
                    'total_debits': total_debits,
                    'total_credits': total_credits,
                    'difference': abs(total_debits - total_credits),
                    'balanced': abs(total_debits - total_credits) < 0.01
                },
                'as_of_date': as_of_date or date.today(),
                'generated_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error generating trial balance: {e}")
            return {'error': f'Error generating trial balance: {str(e)}'}
    
    def get_financial_summary(self, start_date: date = None, end_date: date = None) -> Dict:
        """Get financial summary and statistics"""
        try:
            # Get ledger statistics
            ledger_stats = self.ledger.get_statistics()
            
            # Get credit/debit statistics  
            cd_stats = self.credit_debit.get_statistics()
            
            # Get subsidiary statistics
            sub_stats = self.subcodes.get_statistics()
            
            # Get account statistics
            account_stats = self.accounts.get_account_statistics()
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date or date.today()
                },
                'ledger_statistics': ledger_stats,
                'credit_debit_statistics': cd_stats,
                'subsidiary_statistics': sub_stats,
                'account_statistics': account_stats,
                'generated_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            return {'error': f'Error getting financial summary: {str(e)}'}
    
    def _validate_credit_debit_balance(self, credit_debit_lines: List[Dict], 
                                     total_amount: float) -> bool:
        """Validate that credit/debit lines balance"""
        try:
            total_debits = sum(
                float(line['amount']) for line in credit_debit_lines 
                if line['acct_type'] == 'D'
            )
            total_credits = sum(
                float(line['amount']) for line in credit_debit_lines 
                if line['acct_type'] == 'C'
            )
            
            # Round to avoid floating point precision issues
            total_debits = float(Decimal(str(total_debits)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            total_credits = float(Decimal(str(total_credits)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            total_amount = float(Decimal(str(total_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            # Check if debits equal credits
            debits_credits_balanced = abs(total_debits - total_credits) < 0.01
            
            # Check if either debits or credits equal total amount
            amount_matches = (abs(total_debits - total_amount) < 0.01 or 
                            abs(total_credits - total_amount) < 0.01)
            
            return debits_credits_balanced and amount_matches
            
        except Exception as e:
            logger.error(f"Error validating credit/debit balance: {e}")
            return False
    
    def search_transactions(self, search_term: str, transaction_type: str = None,
                          start_date: date = None, end_date: date = None) -> List[Dict]:
        """Search transactions across all fields"""
        try:
            # Search in main ledger
            ledger_results = self.ledger.search(search_term, transaction_type)
            
            # Search in account descriptions
            account_results = self.credit_debit.search(search_term)
            
            # Search in subsidiary codes
            subsidiary_results = self.subcodes.search(search_term)
            
            # Combine and deduplicate results by number
            all_numbers = set()
            combined_results = []
            
            for result in ledger_results:
                if result['number'] not in all_numbers:
                    all_numbers.add(result['number'])
                    combined_results.append(result)
            
            # Add any additional numbers from account or subsidiary searches
            for result in account_results + subsidiary_results:
                if result['number'] not in all_numbers:
                    ledger_entry = self.ledger.get_by_number(result['number'])
                    if ledger_entry:
                        all_numbers.add(result['number'])
                        combined_results.append(ledger_entry)
            
            # Filter by date if provided
            if start_date or end_date:
                filtered_results = []
                for result in combined_results:
                    result_date = datetime.strptime(result['date'], '%Y-%m-%d').date()
                    if start_date and result_date < start_date:
                        continue
                    if end_date and result_date > end_date:
                        continue
                    filtered_results.append(result)
                combined_results = filtered_results
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return []