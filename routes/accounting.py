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
        """Accounting dashboard"""
        try:
            # Get financial summary
            financial_summary = accounting_service.get_financial_summary()
            
            # Get recent transactions
            recent_vp = accounting_service.ledger.get_all(ledger_type='VP', limit=5)
            recent_cv = accounting_service.ledger.get_all(ledger_type='CV', limit=5)
            
            # Get overdue items
            overdue_items = accounting_service.ledger.get_overdue()
            
            return render_template('accounting/dashboard.html',
                                 financial_summary=financial_summary,
                                 recent_vp=recent_vp,
                                 recent_cv=recent_cv,
                                 overdue_items=overdue_items)
        except Exception as e:
            logger.error(f"Error loading accounting dashboard: {e}")
            flash('Error loading dashboard', 'error')
            return redirect(url_for('dashboard.index'))
    
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
            due_date_str = request.form.get('due_date')
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
            
            # Validate required fields
            if not all([transaction_date, payee_code, total_amount]):
                flash('Transaction date, payee, and amount are required', 'error')
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
            
            # Get subsidiary lines from form
            subsidiary_lines = []
            sub_count = int(request.form.get('sub_line_count', 0))
            
            for i in range(sub_count):
                acct_code = request.form.get(f'sub_acct_code_{i}')
                acct_desc = request.form.get(f'sub_acct_desc_{i}')
                sub_code = request.form.get(f'sub_subsidiary_code_{i}')
                sub_desc = request.form.get(f'sub_subsidiary_desc_{i}')
                amount = request.form.get(f'sub_amount_{i}')
                
                if acct_code and sub_code and amount:
                    subsidiary_lines.append({
                        'acct_code': acct_code,
                        'acct_description': acct_desc or acct_code,
                        'subsidiary_code': sub_code,
                        'subsidiary_description': sub_desc or sub_code,
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
            
            # Get statistics
            cv_stats = accounting_service.ledger.get_statistics(ledger_type='CV')
            
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
            # Get payees
            payees = account_model.get_payees()
            
            # Get bank accounts
            bank_accounts = account_model.get_by_prefix('BANK')
            
            # Get open VP numbers for linking
            open_vps = accounting_service.ledger.get_all(ledger_type='VP', status='active', limit=50)
            
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
            
            # Get credit/debit lines from form (similar to VP creation)
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
            
            # Create check voucher
            success, message, cv_number = accounting_service.create_check_voucher(
                transaction_date=transaction_date,
                payee_code=payee_code,
                total_amount=total_amount,
                vp_number=vp_number,
                check_number=check_number,
                bank_account=bank_account,
                description=description,
                credit_debit_lines=credit_debit_lines if credit_debit_lines else None,
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
    
    # Transaction Details and Management
    @accounting_bp.route('/transaction/<number>')
    @login_required
    @audit_action("VIEW_TRANSACTION")
    def view_transaction(number):
        """View complete transaction details"""
        try:
            transaction = accounting_service.get_transaction(number)
            if not transaction:
                flash('Transaction not found', 'error')
                return redirect(url_for('accounting.dashboard'))
            
            return render_template('accounting/transaction_detail.html',
                                 transaction=transaction)
        except Exception as e:
            logger.error(f"Error viewing transaction {number}: {e}")
            flash('Error loading transaction details', 'error')
            return redirect(url_for('accounting.dashboard'))
    
    @accounting_bp.route('/transaction/<number>/void', methods=['POST'])
    @login_required
    @audit_action("VOID_TRANSACTION")
    def void_transaction(number):
        """Void a transaction"""
        try:
            reason = request.form.get('reason', '').strip()
            if not reason:
                flash('Void reason is required', 'error')
                return redirect(url_for('accounting.view_transaction', number=number))
            
            success, message = accounting_service.void_transaction(
                number=number,
                voided_by=session.get('user_id'),
                reason=reason
            )
            
            if success:
                flash(f'Transaction {number} voided successfully', 'success')
            else:
                flash(f'Failed to void transaction: {message}', 'error')
            
            return redirect(url_for('accounting.view_transaction', number=number))
            
        except Exception as e:
            logger.error(f"Error voiding transaction {number}: {e}")
            flash('An error occurred while voiding the transaction', 'error')
            return redirect(url_for('accounting.view_transaction', number=number))
    
    # Account Management
    @accounting_bp.route('/accounts')
    @login_required
    @audit_action("VIEW_ACCOUNTS")
    def list_accounts():
        """List all accounts (Chart of Accounts)"""
        try:
            # Get accounts grouped by type
            accounts_by_category = account_model.get_accounts_by_category()
            
            # Get account statistics
            account_stats = account_model.get_account_statistics()
            
            return render_template('accounting/accounts/list.html',
                                 accounts_by_category=accounts_by_category,
                                 stats=account_stats)
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            flash('Error loading accounts', 'error')
            return redirect(url_for('accounting.dashboard'))
    
    @accounting_bp.route('/accounts/create', methods=['GET', 'POST'])
    @login_required
    def create_account():
        """Create new account"""
        if request.method == 'GET':
            account_types = ['Company', 'Customer', 'Employee', 'Subsidiary']
            prefixes = account_model.get_account_prefixes()
            return render_template('accounting/accounts/create.html',
                                 account_types=account_types,
                                 prefixes=prefixes)
        
        try:
            acct_code = request.form.get('acct_code', '').strip()
            acct_description = request.form.get('acct_description', '').strip()
            acct_type = request.form.get('acct_type')
            acct_prefix = request.form.get('acct_prefix', '').strip() or None
            
            # Validate required fields
            if not all([acct_code, acct_description, acct_type]):
                flash('Account code, description, and type are required', 'error')
                return redirect(request.url)
            
            # Validate account code
            is_valid, validation_message = account_model.validate_account_code(acct_code)
            if not is_valid:
                flash(f'Invalid account code: {validation_message}', 'error')
                return redirect(request.url)
            
            # Create account
            account_id = account_model.create(acct_code, acct_description, acct_type, acct_prefix)
            
            if account_id:
                flash(f'Account {acct_code} created successfully', 'success')
                return redirect(url_for('accounting.list_accounts'))
            else:
                flash('Failed to create account', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            flash('An error occurred while creating the account', 'error')
            return redirect(request.url)
    
    @accounting_bp.route('/account/<acct_code>')
    @login_required
    @audit_action("VIEW_ACCOUNT_LEDGER")
    def view_account_ledger(acct_code):
        """View account ledger"""
        try:
            # Get date filters
            start_date_str = request.args.get('start_date', '')
            end_date_str = request.args.get('end_date', '')
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            
            # Get account ledger
            ledger_data = accounting_service.get_account_ledger(acct_code, start_date, end_date)
            
            if 'error' in ledger_data:
                flash(ledger_data['error'], 'error')
                return redirect(url_for('accounting.list_accounts'))
            
            return render_template('accounting/accounts/ledger.html',
                                 ledger_data=ledger_data,
                                 acct_code=acct_code,
                                 filters={
                                     'start_date': start_date_str,
                                     'end_date': end_date_str
                                 })
        except Exception as e:
            logger.error(f"Error viewing account ledger {acct_code}: {e}")
            flash('Error loading account ledger', 'error')
            return redirect(url_for('accounting.list_accounts'))
    
    # Reports
    @accounting_bp.route('/reports')
    @login_required
    @audit_action("VIEW_REPORTS")
    def reports():
        """Reports dashboard"""
        return render_template('accounting/reports/index.html')
    
    @accounting_bp.route('/reports/trial-balance')
    @login_required
    @audit_action("VIEW_TRIAL_BALANCE")
    def trial_balance():
        """Trial balance report"""
        try:
            as_of_date_str = request.args.get('as_of_date', '')
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date() if as_of_date_str else date.today()
            
            trial_balance_data = accounting_service.get_trial_balance(as_of_date)
            
            if 'error' in trial_balance_data:
                flash(trial_balance_data['error'], 'error')
                return redirect(url_for('accounting.reports'))
            
            return render_template('accounting/reports/trial_balance.html',
                                 trial_balance_data=trial_balance_data,
                                 as_of_date=as_of_date)
        except Exception as e:
            logger.error(f"Error generating trial balance: {e}")
            flash('Error generating trial balance', 'error')
            return redirect(url_for('accounting.reports'))
    
    # API Endpoints
    @accounting_bp.route('/api/accounts/search')
    @login_required
    def api_search_accounts():
        """API endpoint to search accounts"""
        search_term = request.args.get('q', '').strip()
        acct_type = request.args.get('type', '')
        
        if not search_term:
            return jsonify([])
        
        accounts = account_model.search(search_term, acct_type if acct_type else None)
        
        return jsonify([
            {
                'acct_code': account['acct_code'],
                'acct_description': account['acct_description'],
                'acct_type': account['acct_type'],
                'acct_prefix': account['acct_prefix']
            }
            for account in accounts
        ])
    
    @accounting_bp.route('/api/vouchers-payable/search')
    @login_required
    def api_search_vouchers_payable():
        """API endpoint to search active vouchers payable"""
        search_term = request.args.get('q', '').strip()
        
        if not search_term:
            # Return recent active VPs
            vouchers = accounting_service.ledger.get_all(ledger_type='VP', status='active', limit=20)
        else:
            # Search VPs
            vouchers = accounting_service.ledger.search(search_term, 'VP')
            vouchers = [v for v in vouchers if v['status'] == 'active']
        
        return jsonify([
            {
                'number': voucher['number'],
                'payee': voucher['payee'],
                'total_amount': voucher['total_amount'],
                'date': voucher['date'],
                'description': voucher['description']
            }
            for voucher in vouchers
        ])
    
    @accounting_bp.route('/api/transaction/<number>/balance-check')
    @login_required
    def api_transaction_balance_check(number):
        """API endpoint to check transaction balance"""
        try:
            balance_check = accounting_service.credit_debit.validate_entry_balance(number)
            return jsonify(balance_check)
        except Exception as e:
            logger.error(f"Error checking balance for {number}: {e}")
            return jsonify({'error': str(e)}), 500
    
    return accounting_bp