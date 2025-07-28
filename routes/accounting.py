# routes/accounting.py
"""
Accounting Routes - Voucher Payable and Check Voucher Management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date
from utils.decorators import login_required, admin_required, audit_action
from services.accounting_service import AccountingService
from models.account_definition import AccountDefinition
import logging

logger = logging.getLogger(__name__)

def create_accounting_blueprint(db_manager):
    """Create and configure accounting blueprint"""
    
    accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting')
    accounting_service = AccountingService(db_manager)
    account_model = AccountDefinition(db_manager)
    
    # Dashboard
    @accounting_bp.route('/')
    @login_required
    @audit_action("VIEW_ACCOUNTING_DASHBOARD")
    def dashboard():
        """Accounting dashboard - safe version"""
        try:
            # Initialize default values
            financial_summary = {
                'total_vouchers': 0,
                'total_amount': 0,
                'pending_vouchers': 0,
                'pending_amount': 0,
                'monthly_trends': []
            }
            recent_vp = []
            recent_cv = []
            overdue_items = []
            
            try:
                # Try to get financial summary
                if hasattr(accounting_service, 'get_financial_summary'):
                    financial_summary = accounting_service.get_financial_summary()
            except Exception as e:
                logger.warning(f"Could not get financial summary: {e}")
            
            try:
                # Try to get recent VP transactions
                if hasattr(accounting_service, 'ledger') and hasattr(accounting_service.ledger, 'get_all'):
                    recent_vp = accounting_service.ledger.get_all(ledger_type='VP', limit=5) or []
            except Exception as e:
                logger.warning(f"Could not get recent VP transactions: {e}")
            
            try:
                # Try to get recent CV transactions  
                if hasattr(accounting_service, 'ledger') and hasattr(accounting_service.ledger, 'get_all'):
                    recent_cv = accounting_service.ledger.get_all(ledger_type='CV', limit=5) or []
            except Exception as e:
                logger.warning(f"Could not get recent CV transactions: {e}")
            
            try:
                # Try to get overdue items
                if hasattr(accounting_service, 'ledger') and hasattr(accounting_service.ledger, 'get_overdue'):
                    overdue_items = accounting_service.ledger.get_overdue() or []
            except Exception as e:
                logger.warning(f"Could not get overdue items: {e}")
            
            # Create basic statistics from available data
            vp_stats = {
                'total_count': len(recent_vp),
                'total_amount': sum(float(vp.get('total_amount', 0)) for vp in recent_vp if isinstance(vp, dict)),
                'pending_count': len([vp for vp in recent_vp if isinstance(vp, dict) and vp.get('status') == 'active']),
            }
            
            cv_stats = {
                'total_count': len(recent_cv),
                'total_amount': sum(float(cv.get('total_amount', 0)) for cv in recent_cv if isinstance(cv, dict)),
            }
            
            return render_template('accounting/dashboard.html',
                                financial_summary=financial_summary,
                                recent_vp=recent_vp,
                                recent_cv=recent_cv,
                                overdue_items=overdue_items,
                                vp_stats=vp_stats,
                                cv_stats=cv_stats)
        except Exception as e:
            logger.error(f"Error loading accounting dashboard: {e}")
            flash('Dashboard is starting up. Some features may be limited.', 'info')
            
            # Return minimal dashboard
            return render_template('accounting/dashboard.html',
                                financial_summary={'total_vouchers': 0, 'total_amount': 0},
                                recent_vp=[],
                                recent_cv=[],
                                overdue_items=[],
                                vp_stats={'total_count': 0, 'total_amount': 0},
                                cv_stats={'total_count': 0, 'total_amount': 0})
    
    # Vouchers Payable Routes
    @accounting_bp.route('/vouchers-payable')
    @login_required
    @audit_action("VIEW_VOUCHERS_PAYABLE")
    def list_vouchers_payable():
        """List all vouchers payable"""
        try:
            page = request.args.get('page', 1, type=int)
            limit = 25
            offset = (page - 1) * limit
            
            # Get filters
            status_filter = request.args.get('status', '')
            payee_filter = request.args.get('payee', '')
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            
            # Convert date strings
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            
            # Get vouchers
            vouchers = accounting_service.ledger.get_all(
                ledger_type='VP',
                status=status_filter if status_filter else None,
                start_date=start_date_obj,
                end_date=end_date_obj,
                limit=limit,
                offset=offset
            )
            
            # Filter by payee if specified
            if payee_filter:
                vouchers = [v for v in vouchers if payee_filter.lower() in v['payee'].lower()]
            
            # Get statistics
            vp_stats = accounting_service.ledger.get_statistics(ledger_type='VP')
            
            return render_template('accounting/vouchers_payable/list.html',
                                 vouchers=vouchers,
                                 stats=vp_stats,
                                 current_page=page,
                                 filters={
                                     'status': status_filter,
                                     'payee': payee_filter,
                                     'start_date': start_date,
                                     'end_date': end_date
                                 })
        except Exception as e:
            logger.error(f"Error listing vouchers payable: {e}")
            flash('Error loading vouchers payable', 'error')
            return redirect(url_for('accounting.dashboard'))
    
    @accounting_bp.route('/vouchers-payable/create', methods=['GET', 'POST'])
    @login_required
    def create_voucher_payable():
        """Create new voucher payable"""
        if request.method == 'GET':
            # Get payees (accounts that can receive payments)
            payees = account_model.get_payees()
            
            # Get expense accounts for default credit/debit lines
            expense_accounts = account_model.get_by_prefix('EXP')
            
            return render_template('accounting/vouchers_payable/create.html',
                                 payees=payees,
                                 expense_accounts=expense_accounts)
        
        try:
            # Get form data
            transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d').date()
            payee_code = request.form.get('payee_code')
            total_amount = float(request.form.get('total_amount'))
            description = request.form.get('description', '').strip()
            due_date = request.form.get('due_date')
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None
            
            # Get credit/debit lines from form
            credit_debit_lines = []
            cd_count = int(request.form.get('cd_line_count', 0))
            
            for i in range(cd_count):
                acct_code = request.form.get(f'cd_acct_code_{i}')
                acct_desc = request.form.get(f'cd_acct_desc_{i}')
                amount = request.form.get(f'cd_amount_{i}')
                acct_type = request.form.get(f'cd_acct_type_{i}')
                
                if acct_code and amount and acct_type:
                    credit_debit_lines.append({
                        'acct_code': acct_code,
                        'acct_description': acct_desc or acct_code,
                        'amount': float(amount),
                        'acct_type': acct_type
                    })
            
            # Get subsidiary lines from form
            subsidiary_lines = []
            sub_count = int(request.form.get('sub_line_count', 0))
            
            for i in range(sub_count):
                sub_code = request.form.get(f'sub_code_{i}')
                sub_desc = request.form.get(f'sub_desc_{i}')
                amount = request.form.get(f'sub_amount_{i}')
                
                if sub_code and amount:
                    subsidiary_lines.append({
                        'sub_code': sub_code,
                        'description': sub_desc or sub_code,
                        'amount': float(amount)
                    })
            
            # Create voucher payable
            success, message, vp_number = accounting_service.create_voucher_payable(
                transaction_date=transaction_date,
                payee_code=payee_code,
                total_amount=total_amount,
                description=description,
                due_date=due_date,
                credit_debit_lines=credit_debit_lines if credit_debit_lines else None,
                subsidiary_lines=subsidiary_lines if subsidiary_lines else None,
                created_by=session.get('user_id')
            )
            
            if success:
                flash(f'Voucher Payable {vp_number} created successfully', 'success')
                return redirect(url_for('accounting.view_transaction', number=vp_number))
            else:
                flash(f'Failed to create Voucher Payable: {message}', 'error')
                return redirect(request.url)
                
        except ValueError as e:
            flash('Invalid date or amount format', 'error')
            return redirect(request.url)
        except Exception as e:
            logger.error(f"Error creating voucher payable: {e}")
            flash('An error occurred while creating the voucher payable', 'error')
            return redirect(request.url)
    
    # Check Vouchers Routes
    @accounting_bp.route('/check-vouchers')
    @login_required
    @audit_action("VIEW_CHECK_VOUCHERS")
    def list_check_vouchers():
        """List all check vouchers"""
        try:
            page = request.args.get('page', 1, type=int)
            limit = 25
            offset = (page - 1) * limit
            
            # Get filters
            payee_filter = request.args.get('payee', '')
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            
            # Convert date strings
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            
            # Get check vouchers
            check_vouchers = accounting_service.ledger.get_all(
                ledger_type='CV',
                start_date=start_date_obj,
                end_date=end_date_obj,
                limit=limit,
                offset=offset
            )
            
            # Filter by payee if specified
            if payee_filter:
                check_vouchers = [cv for cv in check_vouchers if payee_filter.lower() in cv['payee'].lower()]
            
            # Get enhanced statistics
            cv_stats = accounting_service.ledger.get_statistics(ledger_type='CV')
            
            # Add monthly statistics
            from datetime import datetime, timedelta
            current_month = datetime.now().month
            current_year = datetime.now().year
            month_start = datetime(current_year, current_month, 1).date()
            
            month_cvs = accounting_service.ledger.get_all(
                ledger_type='CV',
                start_date=month_start,
                limit=1000  # Get all for the month
            )
            
            # Calculate monthly stats
            month_count = len(month_cvs)
            month_amount = sum(cv.get('total_amount', 0) for cv in month_cvs)
            
            # Enhance stats
            if not cv_stats.get('check_vouchers'):
                cv_stats['check_vouchers'] = {}
            
            cv_stats['check_vouchers']['this_month_count'] = month_count
            cv_stats['check_vouchers']['this_month_amount'] = month_amount
            
            return render_template('accounting/check_vouchers/list.html',
                                 check_vouchers=check_vouchers,
                                 stats=cv_stats,
                                 current_page=page,
                                 filters={
                                     'payee': payee_filter,
                                     'start_date': start_date,
                                     'end_date': end_date
                                 })
        except Exception as e:
            logger.error(f"Error listing check vouchers: {e}")
            flash('Error loading check vouchers', 'error')
            return redirect(url_for('accounting.dashboard'))

    @accounting_bp.route('/check-vouchers/create', methods=['GET', 'POST'])
    @login_required
    def create_check_voucher():
        """Create new check voucher"""
        if request.method == 'GET':
            # Get payees (accounts that can receive payments)
            payees = account_model.get_payees()
            
            # Get bank accounts
            bank_accounts = account_model.get_by_prefix('BANK')
            if not bank_accounts:
                # Add default bank accounts if none exist
                bank_accounts = [
                    {'code': '1010', 'description': 'Primary Checking Account'},
                    {'code': '1020', 'description': 'Secondary Checking Account'},
                    {'code': '1030', 'description': 'Petty Cash Account'}
                ]
            
            # Get open VP numbers for linking (active VPs that haven't been fully paid)
            open_vps = accounting_service.ledger.get_all(
                ledger_type='VP', 
                status='active', 
                limit=100
            )
            
            return render_template('accounting/check_vouchers/create.html',
                                 payees=payees,
                                 bank_accounts=bank_accounts,
                                 open_vps=open_vps)
        
        try:
            # Get form data
            transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d').date()
            payee_code = request.form.get('payee_code')
            total_amount = float(request.form.get('total_amount'))
            vp_number = request.form.get('vp_number', '').strip() or None
            check_number = request.form.get('check_number', '').strip() or None
            bank_account = request.form.get('bank_account')
            description = request.form.get('description', '').strip()
            
            # Validate required fields
            if not all([transaction_date, payee_code, total_amount, bank_account]):
                flash('Transaction date, payee, amount, and bank account are required', 'error')
                return redirect(request.url)
            
            if total_amount <= 0:
                flash('Amount must be greater than zero', 'error')
                return redirect(request.url)
            
            # Get credit/debit lines from form
            credit_debit_lines = []
            cd_count = int(request.form.get('cd_line_count', 0))
            
            for i in range(cd_count):
                acct_code = request.form.get(f'cd_acct_code_{i}')
                acct_desc = request.form.get(f'cd_acct_desc_{i}')
                amount = request.form.get(f'cd_amount_{i}')
                acct_type = request.form.get(f'cd_acct_type_{i}')
                
                if acct_code and amount and acct_type:
                    credit_debit_lines.append({
                        'acct_code': acct_code,
                        'acct_description': acct_desc or acct_code,
                        'amount': float(amount),
                        'acct_type': acct_type
                    })
            
            # If no manual credit/debit lines, create automatic entries
            if not credit_debit_lines:
                # Default CV entries: Debit A/P, Credit Cash
                if vp_number:
                    # If paying a VP, debit Accounts Payable
                    credit_debit_lines = [
                        {
                            'acct_code': '2000',  # Accounts Payable
                            'acct_description': 'Accounts Payable',
                            'amount': total_amount,
                            'acct_type': 'debit'
                        },
                        {
                            'acct_code': bank_account,
                            'acct_description': 'Bank Account',
                            'amount': total_amount,
                            'acct_type': 'credit'
                        }
                    ]
                else:
                    # Direct payment, debit expense account
                    credit_debit_lines = [
                        {
                            'acct_code': '5000',  # General Expense
                            'acct_description': 'General Expense',
                            'amount': total_amount,
                            'acct_type': 'debit'
                        },
                        {
                            'acct_code': bank_account,
                            'acct_description': 'Bank Account',
                            'amount': total_amount,
                            'acct_type': 'credit'
                        }
                    ]
            
            # Create check voucher
            success, message, cv_number = accounting_service.create_check_voucher(
                transaction_date=transaction_date,
                payee_code=payee_code,
                total_amount=total_amount,
                vp_number=vp_number,
                check_number=check_number,
                bank_account=bank_account,
                description=description,
                credit_debit_lines=credit_debit_lines,
                created_by=session.get('user_id')
            )
            
            if success:
                flash(f'Check Voucher {cv_number} created successfully', 'success')
                return redirect(url_for('accounting.view_transaction', number=cv_number))
            else:
                flash(f'Failed to create Check Voucher: {message}', 'error')
                return redirect(request.url)
                
        except ValueError as e:
            flash('Invalid date or amount format', 'error')
            return redirect(request.url)
        except Exception as e:
            logger.error(f"Error creating check voucher: {e}")
            flash('An error occurred while creating the check voucher', 'error')
            return redirect(request.url)

    # Transaction View Route
    @accounting_bp.route('/transactions/<transaction_number>')
    @login_required
    @audit_action("VIEW_TRANSACTION_DETAILS")
    def view_transaction(transaction_number):
        """View detailed transaction information"""
        try:
            # Get transaction details
            transaction = accounting_service.ledger.get_by_number(transaction_number)
            
            if not transaction:
                flash('Transaction not found', 'error')
                return redirect(url_for('accounting.dashboard'))
            
            # Get credit/debit lines
            credit_debit_lines = accounting_service.get_transaction_lines(transaction_number)
            
            # Get subsidiary lines if any
            subsidiary_lines = accounting_service.get_subsidiary_lines(transaction_number)
            
            # Get related transactions (e.g., CV for a VP)
            related_transactions = accounting_service.get_related_transactions(transaction_number)
            
            return render_template('accounting/transaction_detail.html',
                                 transaction=transaction,
                                 credit_debit_lines=credit_debit_lines,
                                 subsidiary_lines=subsidiary_lines,
                                 related_transactions=related_transactions)
                                 
        except Exception as e:
            logger.error(f"Error viewing transaction {transaction_number}: {e}")
            flash('Error loading transaction details', 'error')
            return redirect(url_for('accounting.dashboard'))

    # Transaction Voiding Route (for both VP and CV)
    @accounting_bp.route('/transactions/<transaction_number>/void', methods=['POST'])
    @login_required
    @admin_required
    @audit_action("VOID_TRANSACTION")
    def void_transaction(transaction_number):
        """Void a transaction (VP or CV)"""
        try:
            success, message = accounting_service.void_transaction(
                transaction_number=transaction_number,
                voided_by=session.get('user_id')
            )
            
            return jsonify({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            logger.error(f"Error voiding transaction {transaction_number}: {e}")
            return jsonify({
                'success': False,
                'message': 'An error occurred while voiding the transaction'
            })

    # AJAX endpoint for VP details
    @accounting_bp.route('/api/vp/<vp_number>')
    @login_required
    def api_get_vp_details(vp_number):
        """API endpoint to get VP details for CV creation"""
        try:
            vp = accounting_service.ledger.get_by_number(vp_number)
            if not vp:
                return jsonify({'error': 'VP not found'}), 404
            
            return jsonify({
                'success': True,
                'vp': {
                    'number': vp['number'],
                    'payee_code': vp['payee_code'],
                    'payee': vp['payee'],
                    'total_amount': vp['total_amount'],
                    'description': vp['description'],
                    'due_date': vp.get('due_date'),
                    'remaining_amount': vp.get('remaining_amount', vp['total_amount'])
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting VP details {vp_number}: {e}")
            return jsonify({'error': 'Error retrieving VP details'}), 500

    
    # Return the blueprint
    return accounting_bp