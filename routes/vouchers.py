# routes/vouchers.py
"""
Voucher Management Routes - Flask Blueprint for voucher-related endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import login_required, admin_required, audit_action
from services.voucher_service import VoucherService
from services.company_service import CompanyService
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)

def create_vouchers_blueprint(db_manager):
    """Create and configure vouchers blueprint"""
    
    vouchers_bp = Blueprint('vouchers', __name__, url_prefix='/vouchers')
    voucher_service = VoucherService(db_manager)
    company_service = CompanyService(db_manager)
    
    # Vouchers Payable Routes
    @vouchers_bp.route('/payable')
    @login_required
    @audit_action("VIEW_VOUCHERS_PAYABLE")
    def list_vouchers_payable():
        """List Vouchers Payable"""
        try:
            # Get filter parameters
            status = request.args.get('status', '')
            payee_code = request.args.get('payee_code', '')
            
            # For non-admin users, filter by their created vouchers
            created_by = None if session.get('role') == 'admin' else session.get('user_id')
            
            vouchers = voucher_service.get_vouchers_list(
                voucher_type='VP',
                status=status if status else None,
                payee_code=payee_code if payee_code else None,
                created_by=created_by
            )
            
            # Get statistics
            stats = voucher_service.get_voucher_statistics(
                user_id=created_by
            )
            
            # Get companies for filter
            companies = company_service.get_all_companies()
            
            return render_template('vouchers/payable/list.html',
                                 vouchers=vouchers,
                                 stats=stats,
                                 companies=companies,
                                 current_status=status,
                                 current_payee=payee_code)
        except Exception as e:
            logger.error(f"Error loading vouchers payable: {e}")
            flash('Error loading vouchers', 'error')
            return redirect(url_for('dashboard.index'))
    
    @vouchers_bp.route('/payable/create', methods=['GET', 'POST'])
    @login_required
    def create_voucher_payable():
        """Create new Voucher Payable"""
        
        if request.method == 'GET':
            # Get account codes and companies for form
            account_codes = voucher_service.get_account_codes()
            companies = company_service.get_all_companies()
            
            return render_template('vouchers/payable/create.html',
                                 account_codes=account_codes,
                                 companies=companies)
        
        # Handle POST request
        try:
            payee_code = request.form.get('payee_code', '').strip()
            payee = request.form.get('payee', '').strip()
            total_amount = request.form.get('total_amount', '0')
            description = request.form.get('description', '').strip()
            due_date = request.form.get('due_date', '').strip() or None
            
            # Parse line items (expecting JSON format or form array)
            line_items = []
            
            # Handle multiple line items from form
            line_count = 0
            while f'line_acct_code_{line_count}' in request.form:
                line_acct_code = request.form.get(f'line_acct_code_{line_count}', '').strip()
                line_description = request.form.get(f'line_description_{line_count}', '').strip()
                line_amount = request.form.get(f'line_amount_{line_count}', '0')
                
                if line_acct_code and line_amount:
                    try:
                        line_items.append({
                            'acct_code': line_acct_code,
                            'acct_description': line_description,
                            'amount': Decimal(line_amount)
                        })
                    except InvalidOperation:
                        flash(f'Invalid amount in line item {line_count + 1}', 'error')
                        return redirect(request.url)
                
                line_count += 1
            
            # If no line items from form, create single line item
            if not line_items:
                expense_code = request.form.get('expense_code', '5000')  # Default to general expenses
                line_items = [{
                    'acct_code': expense_code,
                    'acct_description': description or 'General Expense',
                    'amount': Decimal(total_amount)
                }]
            
            # Validate required fields
            if not all([payee_code, payee, total_amount]):
                flash('Payee code, payee name, and amount are required', 'error')
                return redirect(request.url)
            
            try:
                total_amount = Decimal(total_amount)
            except InvalidOperation:
                flash('Invalid total amount', 'error')
                return redirect(request.url)
            
            # Create voucher
            success, message, voucher_number = voucher_service.create_voucher_payable(
                payee_code=payee_code,
                payee=payee,
                total_amount=total_amount,
                description=description,
                due_date=due_date,
                line_items=line_items,
                created_by=session.get('user_id')
            )
            
            if success:
                flash(f'Voucher Payable {voucher_number} created successfully', 'success')
                return redirect(url_for('vouchers.view_voucher', voucher_number=voucher_number))
            else:
                flash(f'Failed to create voucher: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating voucher payable: {e}")
            flash('An error occurred while creating the voucher', 'error')
            return redirect(request.url)
    
    # Check Vouchers Routes
    @vouchers_bp.route('/check')
    @login_required
    @audit_action("VIEW_CHECK_VOUCHERS")
    def list_check_vouchers():
        """List Check Vouchers"""
        try:
            created_by = None if session.get('role') == 'admin' else session.get('user_id')
            
            vouchers = voucher_service.get_vouchers_list(
                voucher_type='CV',
                created_by=created_by
            )
            
            stats = voucher_service.get_voucher_statistics(user_id=created_by)
            
            return render_template('vouchers/check/list.html',
                                 vouchers=vouchers,
                                 stats=stats)
        except Exception as e:
            logger.error(f"Error loading check vouchers: {e}")
            flash('Error loading check vouchers', 'error')
            return redirect(url_for('dashboard.index'))
    
    @vouchers_bp.route('/check/create', methods=['GET', 'POST'])
    @login_required
    def create_check_voucher():
        """Create new Check Voucher"""
        
        if request.method == 'GET':
            # Get pending VP vouchers for payment
            pending_vps = voucher_service.get_vouchers_list(
                voucher_type='VP',
                status='active'
            )
            
            companies = company_service.get_all_companies()
            
            return render_template('vouchers/check/create.html',
                                 pending_vps=pending_vps,
                                 companies=companies)
        
        # Handle POST request
        try:
            vp_number = request.form.get('vp_number', '').strip() or None
            payee_code = request.form.get('payee_code', '').strip()
            payee = request.form.get('payee', '').strip()
            amount = request.form.get('amount', '0')
            check_number = request.form.get('check_number', '').strip()
            bank_account = request.form.get('bank_account', '1010')  # Default bank account
            check_date = request.form.get('check_date', '').strip() or None
            
            try:
                amount = Decimal(amount)
            except InvalidOperation:
                flash('Invalid amount', 'error')
                return redirect(request.url)
            
            if not vp_number and not all([payee_code, payee]):
                flash('Either select a VP or provide payee details', 'error')
                return redirect(request.url)
            
            # Create check voucher
            success, message, cv_number = voucher_service.create_check_voucher(
                vp_number=vp_number,
                payee_code=payee_code,
                payee=payee,
                amount=amount,
                check_number=check_number,
                bank_account=bank_account,
                check_date=check_date,
                created_by=session.get('user_id')
            )
            
            if success:
                flash(f'Check Voucher {cv_number} created successfully', 'success')
                return redirect(url_for('vouchers.view_voucher', voucher_number=cv_number))
            else:
                flash(f'Failed to create check voucher: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating check voucher: {e}")
            flash('An error occurred while creating the check voucher', 'error')
            return redirect(request.url)
    
    # Common Voucher Routes
    @vouchers_bp.route('/<voucher_number>')
    @login_required
    @audit_action("VIEW_VOUCHER_DETAILS")
    def view_voucher(voucher_number):
        """View voucher details"""
        try:
            voucher_details = voucher_service.get_voucher_details(voucher_number)
            
            if not voucher_details.get('voucher'):
                flash('Voucher not found', 'error')
                return redirect(url_for('vouchers.list_vouchers_payable'))
            
            # Check permissions - users can only view their own vouchers unless admin
            voucher = voucher_details['voucher']
            if (session.get('role') != 'admin' and 
                voucher['created_by'] != session.get('user_id')):
                flash('Permission denied', 'error')
                return redirect(url_for('dashboard.index'))
            
            return render_template('vouchers/view.html',
                                 voucher=voucher,
                                 line_items=voucher_details.get('line_items', []),
                                 subcodes=voucher_details.get('subcodes', []))
        except Exception as e:
            logger.error(f"Error viewing voucher {voucher_number}: {e}")
            flash('Error loading voucher details', 'error')
            return redirect(url_for('vouchers.list_vouchers_payable'))
    
    @vouchers_bp.route('/search')
    @login_required
    def search_vouchers():
        """Search vouchers"""
        try:
            search_term = request.args.get('q', '').strip()
            voucher_type = request.args.get('type', '')
            
            if not search_term:
                flash('Please enter a search term', 'warning')
                return redirect(url_for('vouchers.list_vouchers_payable'))
            
            vouchers = voucher_service.search_vouchers(
                search_term=search_term,
                voucher_type=voucher_type if voucher_type else None
            )
            
            # Filter by user permissions
            if session.get('role') != 'admin':
                vouchers = [v for v in vouchers if v['created_by'] == session.get('user_id')]
            
            return render_template('vouchers/search_results.html',
                                 vouchers=vouchers,
                                 search_term=search_term,
                                 voucher_type=voucher_type)
                                 
        except Exception as e:
            logger.error(f"Error searching vouchers: {e}")
            flash('Error occurred during search', 'error')
            return redirect(url_for('vouchers.list_vouchers_payable'))
    
    # API Endpoints
    @vouchers_bp.route('/api/vp/<vp_number>')
    @login_required
    def api_get_vp_details(vp_number):
        """API endpoint to get VP details for CV creation"""
        try:
            voucher = voucher_service.get_voucher_by_number(vp_number)
            if not voucher:
                return jsonify({'error': 'Voucher not found'}), 404
            
            # Check permissions
            if (session.get('role') != 'admin' and 
                voucher['created_by'] != session.get('user_id')):
                return jsonify({'error': 'Permission denied'}), 403
            
            return jsonify({
                'voucher_number': voucher['number'],
                'payee_code': voucher['payee_code'],
                'payee': voucher['payee'],
                'amount': float(voucher['total_amount']),
                'description': voucher['description'],
                'status': voucher['status']
            })
        except Exception as e:
            logger.error(f"Error getting VP details {vp_number}: {e}")
            return jsonify({'error': 'Failed to get voucher details'}), 500
    
    @vouchers_bp.route('/api/stats')
    @login_required
    def api_voucher_stats():
        """API endpoint for voucher statistics"""
        try:
            user_id = None if session.get('role') == 'admin' else session.get('user_id')
            stats = voucher_service.get_voucher_statistics(user_id=user_id)
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting voucher stats: {e}")
            return jsonify({'error': 'Failed to get statistics'}), 500
    
    @vouchers_bp.route('/api/account-codes')
    @login_required
    def api_account_codes():
        """API endpoint to get account codes"""
        try:
            acct_type = request.args.get('type')
            account_codes = voucher_service.get_account_codes(acct_type=acct_type)
            
            return jsonify([
                {
                    'code': acc['acct_code'],
                    'description': acc['acct_description'],
                    'type': acc['acct_type'],
                    'display': f"{acc['acct_code']} - {acc['acct_description']}"
                }
                for acc in account_codes
            ])
        except Exception as e:
            logger.error(f"Error getting account codes: {e}")
            return jsonify({'error': 'Failed to get account codes'}), 500
    
    return vouchers_bp