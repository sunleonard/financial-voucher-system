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
            
            return render_template('accounting/dashboard.html',
                                 financial_summary=financial_summary,
                                 recent_vp=recent_vp,
                                 recent_cv=recent_cv,
                                 overdue_items=overdue_items)
                                 
        except Exception as e:
            logger.error(f"Error loading accounting dashboard: {e}")
            flash('Error loading dashboard', 'error')
            return redirect(url_for('dashboard.index'))

    # ====== PAYEE CRUD ROUTES ======
    
    @accounting_bp.route('/payees')
    @login_required
    @audit_action("VIEW_PAYEES")
    def list_payees():
        """List all payees with search and filtering"""
        try:
            # Get filter parameters
            search_term = request.args.get('search', '').strip()
            payee_type = request.args.get('type', '')
            page = request.args.get('page', 1, type=int)
            
            # Get payees with filtering
            payees = account_model.get_payees(
                search_term=search_term if search_term else None,
                payee_type=payee_type if payee_type else None
            )
            
            # Calculate summary statistics
            summary_stats = account_model.get_payee_statistics()
            
            return render_template('accounting/payees/list.html',
                                 payees=payees,
                                 summary_stats=summary_stats,
                                 current_search=search_term,
                                 current_type=payee_type,
                                 page=page)
                                 
        except Exception as e:
            logger.error(f"Error listing payees: {e}")
            flash('Error loading payees', 'error')
            return redirect(url_for('accounting.dashboard'))

    @accounting_bp.route('/payees/create', methods=['GET', 'POST'])
    @login_required
    @audit_action("CREATE_PAYEE")
    def create_payee():
        """Create new payee"""
        if request.method == 'GET':
            return render_template('accounting/payees/create.html')
        
        try:
            # Get form data
            payee_name = request.form.get('payee_name', '').strip()
            payee_type = request.form.get('payee_type', 'Vendor')
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            address = request.form.get('address', '').strip()
            payment_terms = request.form.get('payment_terms', '')
            tax_id = request.form.get('tax_id', '').strip()
            
            if not payee_name:
                flash('Payee name is required', 'error')
                return redirect(request.url)
            
            # Generate payee code based on type
            type_prefixes = {
                'Company': 'COMP',
                'Vendor': 'VEND',
                'Customer': 'CUST',
                'Employee': 'EMP'
            }
            
            prefix = type_prefixes.get(payee_type, 'PAYEE')
            
            # Get next available code
            existing_payees = account_model.get_by_prefix(prefix)
            next_number = len(existing_payees) + 1
            payee_code = f"{prefix}{next_number:03d}"
            
            # Check if code already exists and increment if needed
            while account_model.get_by_code(payee_code):
                next_number += 1
                payee_code = f"{prefix}{next_number:03d}"
            
            # Create payee account
            account_id = account_model.create(
                acct_code=payee_code,
                acct_description=payee_name,
                acct_type=payee_type,
                acct_prefix=prefix,
                contact_email=contact_email,
                contact_phone=contact_phone,
                address=address,
                payment_terms=payment_terms,
                tax_id=tax_id
            )
            
            if account_id:
                flash(f'Payee {payee_code} created successfully', 'success')
                return redirect(url_for('accounting.view_payee', payee_code=payee_code))
            else:
                flash('Failed to create payee', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating payee: {e}")
            flash('An error occurred while creating the payee', 'error')
            return redirect(request.url)

    @accounting_bp.route('/payees/<payee_code>')
    @login_required
    @audit_action("VIEW_PAYEE_DETAILS")
    def view_payee(payee_code):
        """View payee details and transaction history"""
        try:
            # Get payee details
            payee = account_model.get_by_code(payee_code)
            
            if not payee:
                flash('Payee not found', 'error')
                return redirect(url_for('accounting.list_payees'))
            
            # Get payee transactions
            transactions = []
            try:
                if hasattr(accounting_service, 'get_payee_transactions'):
                    transactions = accounting_service.get_payee_transactions(payee_code)
            except Exception as e:
                logger.warning(f"Could not get payee transactions: {e}")
            
            # Calculate outstanding balance
            outstanding_balance = 0.0
            try:
                if hasattr(accounting_service, 'get_payee_balance'):
                    outstanding_balance = accounting_service.get_payee_balance(payee_code)
            except Exception as e:
                logger.warning(f"Could not calculate payee balance: {e}")
            
            return render_template('accounting/payees/view.html',
                                 payee=payee,
                                 transactions=transactions,
                                 outstanding_balance=outstanding_balance)
                                 
        except Exception as e:
            logger.error(f"Error viewing payee {payee_code}: {e}")
            flash('Error loading payee details', 'error')
            return redirect(url_for('accounting.list_payees'))

    @accounting_bp.route('/payees/<payee_code>/edit', methods=['GET', 'POST'])
    @login_required
    @audit_action("EDIT_PAYEE")
    def edit_payee(payee_code):
        """Edit payee details"""
        try:
            # Get payee details
            payee = account_model.get_by_code(payee_code)
            
            if not payee:
                flash('Payee not found', 'error')
                return redirect(url_for('accounting.list_payees'))
            
            if request.method == 'GET':
                return render_template('accounting/payees/edit.html', payee=payee)
            
            # Handle POST - update payee
            payee_name = request.form.get('payee_name', '').strip()
            payee_type = request.form.get('payee_type', payee['acct_type'])
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            address = request.form.get('address', '').strip()
            payment_terms = request.form.get('payment_terms', '')
            tax_id = request.form.get('tax_id', '').strip()
            
            if not payee_name:
                flash('Payee name is required', 'error')
                return redirect(request.url)
            
            # Update payee
            success = account_model.update(
                account_id=payee['id'],
                acct_description=payee_name,
                acct_type=payee_type,
                contact_email=contact_email,
                contact_phone=contact_phone,
                address=address,
                payment_terms=payment_terms,
                tax_id=tax_id
            )
            
            if success:
                flash(f'Payee {payee_code} updated successfully', 'success')
                return redirect(url_for('accounting.view_payee', payee_code=payee_code))
            else:
                flash('Failed to update payee', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error editing payee {payee_code}: {e}")
            flash('An error occurred while updating the payee', 'error')
            return redirect(url_for('accounting.list_payees'))

    @accounting_bp.route('/payees/<payee_code>/deactivate', methods=['POST'])
    @login_required
    @admin_required
    @audit_action("DEACTIVATE_PAYEE")
    def deactivate_payee(payee_code):
        """Deactivate a payee (soft delete)"""
        try:
            payee = account_model.get_by_code(payee_code)
            
            if not payee:
                return jsonify({'success': False, 'message': 'Payee not found'}), 404
            
            # Check if payee has outstanding transactions
            has_outstanding = False
            try:
                if hasattr(accounting_service, 'payee_has_outstanding_transactions'):
                    has_outstanding = accounting_service.payee_has_outstanding_transactions(payee_code)
            except Exception as e:
                logger.warning(f"Could not check outstanding transactions: {e}")
            
            if has_outstanding:
                return jsonify({
                    'success': False, 
                    'message': 'Cannot deactivate payee with outstanding transactions'
                }), 400
            
            # Deactivate payee
            success = account_model.deactivate(payee['id'])
            
            if success:
                return jsonify({
                    'success': True, 
                    'message': f'Payee {payee_code} deactivated successfully'
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Failed to deactivate payee'
                }), 500
                
        except Exception as e:
            logger.error(f"Error deactivating payee {payee_code}: {e}")
            return jsonify({
                'success': False, 
                'message': 'An error occurred while deactivating the payee'
            }), 500

    # ====== API ENDPOINTS ======
    
    @accounting_bp.route('/api/accounts/search')
    @login_required
    def api_search_accounts():
        """API endpoint to search accounts"""
        try:
            query = request.args.get('q', '').strip()
            account_type = request.args.get('type', '')
            
            if len(query) < 2:
                return jsonify([])
            
            accounts = account_model.search_accounts(
                search_term=query,
                account_type=account_type if account_type else None
            )
            
            formatted_accounts = [
                {
                    'code': acc['acct_code'],
                    'description': acc['acct_description'],
                    'type': acc['acct_type'],
                    'display': f"{acc['acct_code']} - {acc['acct_description']}"
                }
                for acc in accounts
            ]
            
            return jsonify(formatted_accounts)
            
        except Exception as e:
            logger.error(f"Error searching accounts: {e}")
            return jsonify({'error': 'Failed to search accounts'}), 500

    @accounting_bp.route('/api/accounts/payees')
    @login_required
    def api_get_payees():
        """API endpoint to get payee accounts"""
        try:
            payees = account_model.get_payees()
            
            formatted_payees = [
                {
                    'code': payee['acct_code'],
                    'name': payee['acct_description'],
                    'type': payee['acct_type'],
                    'display': f"{payee['acct_code']} - {payee['acct_description']}"
                }
                for payee in payees
            ]
            
            return jsonify(formatted_payees)
            
        except Exception as e:
            logger.error(f"Error getting payees: {e}")
            return jsonify({'error': 'Failed to get payees'}), 500

    @accounting_bp.route('/api/accounts/by-type/<account_type>')
    @login_required
    def api_get_accounts_by_type(account_type):
        """API endpoint to get accounts by type"""
        try:
            accounts = account_model.get_by_type(account_type)
            
            formatted_accounts = [
                {
                    'code': acc['acct_code'],
                    'description': acc['acct_description'],
                    'type': acc['acct_type'],
                    'display': f"{acc['acct_code']} - {acc['acct_description']}"
                }
                for acc in accounts
            ]
            
            return jsonify(formatted_accounts)
            
        except Exception as e:
            logger.error(f"Error getting accounts by type {account_type}: {e}")
            return jsonify({'error': 'Failed to get accounts'}), 500

    @accounting_bp.route('/api/bank-accounts')
    @login_required
    def api_get_bank_accounts():
        """API endpoint to get bank accounts for check vouchers"""
        try:
            bank_accounts = account_model.get_by_prefix('BANK')
            
            # Add default bank accounts if none exist
            if not bank_accounts:
                bank_accounts = [
                    {'acct_code': '1010', 'acct_description': 'Primary Checking Account', 'acct_type': 'Asset'},
                    {'acct_code': '1020', 'acct_description': 'Secondary Checking Account', 'acct_type': 'Asset'},
                    {'acct_code': '1030', 'acct_description': 'Petty Cash Account', 'acct_type': 'Asset'}
                ]
            
            formatted_accounts = [
                {
                    'code': acc['acct_code'],
                    'description': acc['acct_description'],
                    'display': f"{acc['acct_code']} - {acc['acct_description']}"
                }
                for acc in bank_accounts
            ]
            
            return jsonify(formatted_accounts)
            
        except Exception as e:
            logger.error(f"Error getting bank accounts: {e}")
            return jsonify({'error': 'Failed to get bank accounts'}), 500

    # ====== VOUCHER PAYABLE ROUTES ======
    
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
            payee_filter = request.args.get('payee', '')
            status_filter = request.args.get('status', '')
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            
            # Convert date strings
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            
            # Get vouchers payable with filters
            vouchers = accounting_service.ledger.get_all(
                ledger_type='VP',
                limit=limit,
                offset=offset,
                payee_code=payee_filter if payee_filter else None,
                status=status_filter if status_filter else None,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            
            # Get payees for filter dropdown
            payees = account_model.get_payees()
            
            # Get total count for pagination
            total_count = accounting_service.ledger.count_transactions(
                ledger_type='VP',
                payee_code=payee_filter if payee_filter else None,
                status=status_filter if status_filter else None,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            
            return render_template('accounting/vouchers_payable/list.html',
                                 vouchers=vouchers,
                                 payees=payees,
                                 current_payee=payee_filter,
                                 current_status=status_filter,
                                 current_page=page,
                                 total_count=total_count,
                                 limit=limit,
                                 start_date=start_date,
                                 end_date=end_date)
                                 
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
            
            # Pre-fill payee if provided in query params
            selected_payee = request.args.get('payee')
            
            return render_template('accounting/vouchers_payable/create.html',
                                 payees=payees,
                                 expense_accounts=expense_accounts,
                                 selected_payee=selected_payee)
        
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
    
    # ====== CHECK VOUCHER ROUTES ======
    
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
            vouchers = accounting_service.ledger.get_all(
                ledger_type='CV',
                limit=limit,
                offset=offset,
                payee_code=payee_filter if payee_filter else None,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            
            # Get payees for filter dropdown
            payees = account_model.get_payees()
            
            return render_template('accounting/check_vouchers/list.html',
                                 vouchers=vouchers,
                                 payees=payees,
                                 current_payee=payee_filter,
                                 current_page=page,
                                 start_date=start_date,
                                 end_date=end_date)
                                 
        except Exception as e:
            logger.error(f"Error listing check vouchers: {e}")
            flash('Error loading check vouchers', 'error')
            return redirect(url_for('accounting.dashboard'))

    @accounting_bp.route('/check-vouchers/create', methods=['GET', 'POST'])
    @login_required
    def create_check_voucher():
        """Create new check voucher"""
        if request.method == 'GET':
            # Get payees and bank accounts
            payees = account_model.get_payees()
            
            # Get outstanding VPs for linking
            outstanding_vps = []
            try:
                if hasattr(accounting_service, 'get_outstanding_vps'):
                    outstanding_vps = accounting_service.get_outstanding_vps()
            except Exception as e:
                logger.warning(f"Could not get outstanding VPs: {e}")
            
            # Pre-fill payee if provided in query params
            selected_payee = request.args.get('payee')
            
            return render_template('accounting/check_vouchers/create.html',
                                 payees=payees,
                                 outstanding_vps=outstanding_vps,
                                 selected_payee=selected_payee)
        
        try:
            # Get form data
            check_date = datetime.strptime(request.form.get('check_date'), '%Y-%m-%d').date()
            payee_code = request.form.get('payee_code')
            total_amount = float(request.form.get('total_amount'))
            bank_account = request.form.get('bank_account')
            check_number = request.form.get('check_number', '').strip()
            description = request.form.get('description', '').strip()
            vp_number = request.form.get('vp_number', '').strip()  # Optional VP to link
            
            # Create check voucher
            success, message, cv_number = accounting_service.create_check_voucher(
                check_date=check_date,
                payee_code=payee_code,
                total_amount=total_amount,
                bank_account=bank_account,
                check_number=check_number,
                description=description,
                vp_number=vp_number if vp_number else None,
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

    # ====== TRANSACTION MANAGEMENT ======

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

    @accounting_bp.route('/transactions/<transaction_number>/void', methods=['POST'])
    @login_required
    @admin_required
    @audit_action("VOID_TRANSACTION")
    def void_transaction(transaction_number):
        """Void a transaction (admin only)"""
        try:
            success, message = accounting_service.void_transaction(
                transaction_number=transaction_number,
                voided_by=session.get('user_id'),
                reason=request.form.get('void_reason', 'Manual void by admin')
            )
            
            if success:
                flash(f'Transaction {transaction_number} voided successfully', 'success')
            else:
                flash(f'Failed to void transaction: {message}', 'error')
                
            return redirect(url_for('accounting.view_transaction', number=transaction_number))
            
        except Exception as e:
            logger.error(f"Error voiding transaction {transaction_number}: {e}")
            flash('An error occurred while voiding the transaction', 'error')
            return redirect(url_for('accounting.view_transaction', number=transaction_number))

    # ====== ACCOUNT MANAGEMENT ROUTES ======
    
    @accounting_bp.route('/accounts/create', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def create_account():
        """Create new account definition"""
        if request.method == 'GET':
            return render_template('accounting/accounts/create.html')
        
        # Handle POST - account creation
        try:
            acct_code = request.form.get('acct_code', '').strip().upper()
            acct_description = request.form.get('acct_description', '').strip()
            acct_type = request.form.get('acct_type', 'Company')
            acct_prefix = request.form.get('acct_prefix', '').strip() or None
            
            if not all([acct_code, acct_description]):
                flash('Account code and description are required', 'error')
                return redirect(request.url)
            
            # Check if account code already exists
            existing = account_model.get_by_code(acct_code)
            if existing:
                flash(f'Account code {acct_code} already exists', 'error')
                return redirect(request.url)
            
            # Create account
            account_id = account_model.create(
                acct_code=acct_code,
                acct_description=acct_description,
                acct_type=acct_type,
                acct_prefix=acct_prefix
            )
            
            if account_id:
                flash(f'Account {acct_code} created successfully', 'success')
                # If opened in popup, show success page
                if request.args.get('popup'):
                    return render_template('accounting/accounts/created.html', 
                                         account_code=acct_code)
                else:
                    return redirect(url_for('accounting.list_accounts'))
            else:
                flash('Failed to create account', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            flash('An error occurred while creating the account', 'error')
            return redirect(request.url)

    @accounting_bp.route('/accounts')
    @login_required
    def list_accounts():
        """List all accounts"""
        try:
            accounts = account_model.get_all()
            accounts_by_category = account_model.get_accounts_by_category()
            stats = account_model.get_account_statistics()
            
            return render_template('accounting/accounts/list.html',
                                 accounts=accounts,
                                 accounts_by_category=accounts_by_category,
                                 stats=stats)
                                 
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            flash('Error loading accounts', 'error')
            return redirect(url_for('accounting.dashboard'))

    @accounting_bp.route('/trial-balance')  
    @login_required
    def trial_balance():
        """Trial balance report - placeholder"""
        try:
            accounts = account_model.get_all()
            
            # Simplified trial balance - in real system would calculate from ledger
            trial_balance_data = []
            for account in accounts:
                trial_balance_data.append({
                    'account_code': account['acct_code'],
                    'account_name': account['acct_description'],
                    'account_type': account['acct_type'],
                    'debit_balance': 0.00,  # Would calculate from transactions
                    'credit_balance': 0.00  # Would calculate from transactions
                })
            
            return render_template('accounting/trial_balance.html',
                                 accounts=trial_balance_data)
                                 
        except Exception as e:
            logger.error(f"Error generating trial balance: {e}")
            flash('Error generating trial balance', 'error')
            return redirect(url_for('accounting.dashboard'))

    # Return the blueprint
    return accounting_bp