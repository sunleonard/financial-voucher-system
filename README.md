# 🏦 Financial Voucher Management System

A comprehensive web-based financial management system for handling vouchers payable, check vouchers, and financial ledger management with double-entry bookkeeping, role-based access control, and comprehensive audit logging.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Flask](https://img.shields.io/badge/flask-v2.3+-green.svg)
![SQLite](https://img.shields.io/badge/sqlite-v3.0+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Key Features

### 🔐 User Management & Security
- **Role-based access control** (Admin/User permissions)
- **Secure authentication** with password hashing and salt
- **Session management** with automatic timeouts
- **Account security** (failed login tracking, temporary locking)
- **Comprehensive audit logging** with IP tracking and timestamps

### 📊 Advanced Accounting System
- **Double-entry bookkeeping** with proper debit/credit validation
- **Vouchers Payable (VP)** - Track payment obligations and liabilities
- **Check Vouchers (CV)** - Manage actual payments and disbursements  
- **Chart of Accounts** with structured account coding system
- **Subsidiary tracking** for detailed expense categorization
- **Trial balance** and financial reporting capabilities

### 🏢 Account Management
- **Structured account codes**: Companies, Customers, Vendors, Employees
- **Business type classification** (B2B/B2C accounts)
- **Multi-company support** with proper segregation
- **Account definitions** with types (Assets, Liabilities, Equity, Revenue, Expenses)

### 📈 Dashboard & Analytics
- **Real-time financial summaries** and transaction statistics
- **User activity tracking** and recent transaction monitoring
- **Company-wise breakdowns** and performance metrics
- **Interactive charts** with Chart.js integration
- **Financial health indicators** and overdue payment tracking

### 🔍 Audit & Compliance
- **Comprehensive audit trails** for all financial transactions
- **User activity monitoring** with detailed action logs
- **Transaction history** with before/after value tracking
- **Export capabilities** for compliance reporting
- **Data integrity** validation and error detection

### 🎯 Smart Features
- **Intelligent routing** based on user roles and system state
- **Real-time form validation** with balance checking
- **Responsive design** optimized for desktop and mobile
- **Auto-calculation** of totals and account balances
- **Transaction voiding** with proper audit trails

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Flask 2.3+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/financial-voucher-system.git
cd financial-voucher-system
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Initialize the database:**
```bash
python simple_fix.py  # Creates database with sample data
```

4. **Run the application:**
```bash
python app.py
```

5. **Access the system:**
- Open your browser to `http://localhost:5000`
- Login with default credentials:
  - **Username:** `admin`
  - **Password:** `Admin123!`

## 🏗️ Project Structure

```
financial_voucher_system/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── simple_fix.py                   # Database initialization script
├── troubleshoot.py                 # System diagnostic tool
│
├── core/                           # Core system components
│   ├── database.py                 # Database connection manager
│   ├── logger.py                   # Logging configuration
│   └── security.py                 # Security utilities
│
├── models/                         # Database models & business logic
│   ├── user.py                     # User management model
│   ├── company.py                  # Company/account management
│   ├── ledger.py                   # Main transaction ledger
│   ├── ledger_credit_debit.py      # Double-entry line items
│   ├── ledger_subcodes.py          # Subsidiary expense tracking
│   └── account_definition.py       # Chart of accounts
│
├── services/                       # Business logic services
│   ├── user_service.py            # User management operations
│   ├── company_service.py         # Company management operations  
│   ├── accounting_service.py      # Financial transaction services
│   ├── voucher_service.py         # Voucher management operations
│   ├── dashboard_service.py       # Analytics & dashboard data
│   └── audit_service.py           # Audit logging service
│
├── routes/                         # Flask blueprints (URL routing)
│   ├── auth.py                    # Authentication routes
│   ├── users.py                   # User management routes
│   ├── dashboard.py               # Dashboard routes
│   ├── accounting.py              # Main accounting/voucher routes
│   ├── vouchers.py                # Alternative voucher routes
│   └── companies.py               # Company management routes
│
├── templates/                      # HTML templates
│   ├── base.html                  # Base template with navigation
│   ├── auth/                      # Login/logout pages
│   ├── users/                     # User management interface
│   ├── dashboard/                 # Dashboard and analytics
│   ├── accounting/                # Financial management interface
│   │   ├── dashboard.html         # Accounting dashboard
│   │   └── vouchers_payable/      # VP management templates
│   ├── vouchers/                  # Alternative voucher interface
│   └── companies/                 # Company management interface
│
├── static/                        # Static assets
│   ├── css/                       # Stylesheets
│   ├── js/                        # JavaScript files
│   └── images/                    # Images and icons
│
├── utils/                         # Utility functions
│   ├── decorators.py             # Custom decorators
│   └── helpers.py                # Helper functions
│
└── logs/                          # Application logs
    └── app.log                   # Main log file
```

## 💼 Financial Structure

### Account Code System
The system uses a structured account coding approach:

**Chart of Accounts:**
- **1000-1999**: Assets (Cash, Bank Accounts, Accounts Receivable)
- **2000-2999**: Liabilities (Accounts Payable, Notes Payable)
- **3000-3999**: Equity (Capital, Retained Earnings)
- **4000-4999**: Revenue (Sales, Service Revenue)
- **5000-5999**: Expenses (Operating, Administrative)

**Entity Codes:**
- **CUST001-999**: Customer accounts
- **VEND001-999**: Vendor/supplier accounts  
- **EMP001-999**: Employee accounts
- **COMP001-999**: Company/subsidiary accounts

### Transaction Types
- **VP (Voucher Payable)**: Records payment obligations to vendors
- **CV (Check Voucher)**: Records actual payments and disbursements
- Each transaction includes proper debit/credit entries for double-entry bookkeeping

## 💻 Usage Guide

### Admin Features
- **Financial Management**: Create and manage vouchers payable and check vouchers
- **User Management**: Create, edit, delete, and manage user accounts
- **Company Setup**: Configure companies, vendors, and account structures
- **System Administration**: Access all data and system-wide statistics
- **Audit Monitoring**: Review all system activities and financial transactions
- **Reporting**: Generate financial reports and export data

### User Features  
- **Profile Management**: Update personal information and passwords
- **Voucher Creation**: Create vouchers payable for payment obligations
- **Transaction Tracking**: View assigned transactions and payment status
- **Dashboard Access**: View personal statistics and recent activities
- **Financial Entry**: Input and manage financial transactions within permissions

### Typical Workflow
1. **Setup**: Admin configures companies, vendors, and chart of accounts
2. **VP Creation**: Users create Vouchers Payable for payment obligations
3. **Approval**: Authorized users review and approve payment requests
4. **CV Processing**: Finance team creates Check Vouchers for actual payments
5. **Reporting**: Generate financial reports and audit trails

## 🔧 Development & Maintenance

### Development Mode
```bash
# Enable debug mode
export FLASK_ENV=development
python app.py
```

### Database Management
```bash
# Create fresh database with sample data
python simple_fix.py

# Check system health and diagnose issues
python troubleshoot.py

# Reset database (WARNING: Deletes all data)
rm financial_system.db
python simple_fix.py
```

### Configuration
Key configuration options in `config.py`:
- Database path and connection settings
- Session timeout and security settings
- Logging levels and file locations
- Security keys and password requirements

## 🛠️ Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite (with planned PostgreSQL support)
- **Frontend**: Bootstrap 5, HTML5, JavaScript ES6+
- **Charts & Analytics**: Chart.js for data visualization
- **Icons**: Font Awesome 6
- **Security**: Werkzeug password hashing, session management
- **Logging**: Python logging with file rotation

## 🐛 Recent Fixes & Updates

### v1.2.0 - Template System Fixes
- ✅ **Fixed template naming conflicts** between voucher systems
- ✅ **Resolved routing conflicts** for dual voucher management
- ✅ **Improved error handling** for template not found errors
- ✅ **Enhanced system stability** and user experience

### v1.1.0 - Accounting System Enhancement  
- ✅ **Double-entry bookkeeping** implementation
- ✅ **Advanced ledger structure** with proper audit trails
- ✅ **Chart of accounts** management
- ✅ **Financial reporting** capabilities

## 📋 Roadmap

### Phase 1: Foundation ✅
- [x] User authentication and authorization
- [x] Role-based access control  
- [x] Basic dashboard and user management
- [x] Comprehensive audit logging
- [x] Double-entry accounting system

### Phase 2: Core Features ✅
- [x] Complete voucher management (VP/CV)
- [x] Company and vendor management
- [x] Chart of accounts implementation
- [x] Financial transaction processing
- [x] Basic reporting capabilities

### Phase 3: Advanced Features (In Progress)
- [ ] Advanced financial reporting and analytics
- [ ] Email notifications for approvals
- [ ] Document attachment system
- [ ] Approval workflow management
- [ ] Bank reconciliation features
- [ ] Multi-currency support

### Phase 4: Enterprise Features (Planned)
- [ ] Multi-tenant architecture
- [ ] LDAP/SSO integration
- [ ] Advanced analytics dashboard
- [ ] Mobile application
- [ ] Cloud deployment options
- [ ] API endpoints for integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines for Python code
- Include appropriate comments and docstrings
- Test all changes thoroughly before committing
- Update documentation for new features
- Maintain backward compatibility when possible

## 🆘 Troubleshooting

### Common Issues
1. **Template not found errors**: Run `python troubleshoot.py` to check file structure
2. **Database connection errors**: Ensure database file permissions are correct
3. **Login issues**: Use `python simple_fix.py` to reset admin credentials
4. **Port already in use**: Change port in `app.py` or kill existing processes

### Getting Help
- **System diagnostics**: `python troubleshoot.py`
- **Check logs**: Review files in the `logs/` directory  
- **Reset system**: `python simple_fix.py` for fresh start
- **GitHub Issues**: [Create an issue](https://github.com/YOUR_USERNAME/financial-voucher-system/issues)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- Built with Flask and modern web technologies
- Designed for small to medium business financial management
- Implements proper accounting principles and audit trails
- Created with security and compliance in mind

---

**🚀 Ready to manage your finances professionally!**  
*For support or questions, please open an issue on GitHub.*