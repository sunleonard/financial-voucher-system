# routes/companies.py
"""
Company Management Routes - Flask Blueprint for company-related endpoints
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import login_required, admin_required, audit_action
from services.company_service import CompanyService
import logging

logger = logging.getLogger(__name__)

def create_companies_blueprint(db_manager):
    """Create and configure companies blueprint"""
    
    companies_bp = Blueprint('companies', __name__, url_prefix='/companies')
    company_service = CompanyService(db_manager)
    
    @companies_bp.route('/')
    @admin_required
    @audit_action("VIEW_COMPANIES_LIST")
    def list_companies():
        """Display list of all companies (Admin only)"""
        try:
            companies = company_service.get_all_companies()
            company_stats = company_service.get_company_statistics()
            
            return render_template('companies/list.html', 
                                 companies=companies, 
                                 stats=company_stats)
        except Exception as e:
            logger.error(f"Error loading companies list: {e}")
            flash('Error loading companies list', 'error')
            return redirect(url_for('dashboard.index'))
    
    @companies_bp.route('/create', methods=['GET', 'POST'])
    @admin_required
    def create_company():
        """Create new company form and handler (Admin only)"""
        
        if request.method == 'GET':
            return render_template('companies/create.html')
        
        # Handle POST request
        try:
            company_id = request.form.get('company_id', '').strip().upper()
            company_name = request.form.get('company_name', '').strip()
            business_type = request.form.get('business_type', 'B2B')
            
            # Validate required fields
            if not all([company_id, company_name]):
                flash('Company ID and name are required', 'error')
                return redirect(request.url)
            
            # Validate business type
            if business_type not in ['B2B', 'B2C']:
                flash('Invalid business type', 'error')
                return redirect(request.url)
            
            # Create company
            success, message = company_service.create_company(
                company_id=company_id,
                company_name=company_name,
                business_type=business_type,
                created_by=session.get('user_id')
            )
            
            if success:
                flash(f'Company "{company_name}" created successfully', 'success')
                return redirect(url_for('companies.list_companies'))
            else:
                flash(f'Failed to create company: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating company: {e}")
            flash('An error occurred while creating the company', 'error')
            return redirect(request.url)
    
    @companies_bp.route('/<company_id>')
    @admin_required
    @audit_action("VIEW_COMPANY_DETAILS")
    def view_company(company_id):
        """View company details (Admin only)"""
        try:
            company = company_service.get_company_by_id(company_id)
            if not company:
                flash('Company not found', 'error')
                return redirect(url_for('companies.list_companies'))
            
            # Get users associated with this company
            from services.user_service import UserService
            user_service = UserService(db_manager)
            company_users = user_service.get_users_by_company(company_id)
            
            return render_template('companies/view.html', 
                                 company=company,
                                 users=company_users)
        except Exception as e:
            logger.error(f"Error viewing company {company_id}: {e}")
            flash('Error loading company details', 'error')
            return redirect(url_for('companies.list_companies'))
    
    @companies_bp.route('/<company_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def edit_company(company_id):
        """Edit company form and handler (Admin only)"""
        
        try:
            company = company_service.get_company_by_id(company_id)
            if not company:
                flash('Company not found', 'error')
                return redirect(url_for('companies.list_companies'))
            
            if request.method == 'GET':
                return render_template('companies/edit.html', company=company)
            
            # Handle POST request
            company_name = request.form.get('company_name', '').strip()
            business_type = request.form.get('business_type', 'B2B')
            is_active = 'is_active' in request.form
            
            # Validate required fields
            if not company_name:
                flash('Company name is required', 'error')
                return redirect(request.url)
            
            # Validate business type
            if business_type not in ['B2B', 'B2C']:
                flash('Invalid business type', 'error')
                return redirect(request.url)
            
            # Update company
            success, message = company_service.update_company(
                company_id=company_id,
                company_name=company_name,
                business_type=business_type,
                updated_by=session.get('user_id')
            )
            
            if success:
                flash(f'Company "{company_name}" updated successfully', 'success')
                return redirect(url_for('companies.list_companies'))
            else:
                flash(f'Failed to update company: {message}', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error editing company {company_id}: {e}")
            flash('An error occurred while updating the company', 'error')
            return redirect(url_for('companies.list_companies'))
    
    @companies_bp.route('/<company_id>/delete', methods=['POST'])
    @admin_required
    @audit_action("DELETE_COMPANY")
    def delete_company(company_id):
        """Delete company (Admin only)"""
        try:
            # Get company info for flash message
            company = company_service.get_company_by_id(company_id)
            if not company:
                flash('Company not found', 'error')
                return redirect(url_for('companies.list_companies'))
            
            success, message = company_service.delete_company(
                company_id=company_id,
                deleted_by=session.get('user_id')
            )
            
            if success:
                flash(f'Company "{company["company_name"]}" deleted successfully', 'success')
            else:
                flash(f'Failed to delete company: {message}', 'error')
                
        except Exception as e:
            logger.error(f"Error deleting company {company_id}: {e}")
            flash('An error occurred while deleting the company', 'error')
        
        return redirect(url_for('companies.list_companies'))
    
    @companies_bp.route('/search')
    @admin_required
    def search_companies():
        """Search companies (Admin only)"""
        try:
            search_term = request.args.get('q', '').strip()
            
            if not search_term:
                flash('Please enter a search term', 'warning')
                return redirect(url_for('companies.list_companies'))
            
            companies = company_service.search_companies(search_term)
            
            return render_template('companies/search_results.html', 
                                 companies=companies, 
                                 search_term=search_term)
                                 
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            flash('Error occurred during search', 'error')
            return redirect(url_for('companies.list_companies'))
    
    # API Endpoints
    @companies_bp.route('/api/check-id')
    @admin_required
    def api_check_company_id():
        """API endpoint to check company ID availability"""
        company_id = request.args.get('company_id', '').strip().upper()
        
        if not company_id:
            return jsonify({'available': False, 'message': 'Company ID is required'})
        
        # Check if company ID already exists
        existing = company_service.get_company_by_id(company_id)
        available = existing is None
        
        return jsonify({
            'available': available,
            'message': 'Company ID is available' if available else 'Company ID already exists'
        })
    
    @companies_bp.route('/api/stats')
    @admin_required
    def api_company_stats():
        """API endpoint for company statistics"""
        try:
            stats = company_service.get_company_statistics()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting company stats: {e}")
            return jsonify({'error': 'Failed to get statistics'}), 500
    
    @companies_bp.route('/api/list')
    @login_required
    def api_companies_list():
        """API endpoint to get companies list for dropdowns"""
        try:
            companies = company_service.get_all_companies()
            
            # Format for dropdown use
            companies_list = [
                {
                    'id': company['company_id'],
                    'name': company['company_name'],
                    'display': f"{company['company_name']} ({company['company_id']})",
                    'type': company['business_type']
                }
                for company in companies
            ]
            
            return jsonify(companies_list)
        except Exception as e:
            logger.error(f"Error getting companies list: {e}")
            return jsonify({'error': 'Failed to get companies'}), 500
    
    return companies_bp