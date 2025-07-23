# 🏦 Financial Voucher Management System

A comprehensive web-based financial management system for handling vouchers payable, check vouchers, bank memos, and purchase orders with role-based access control and audit logging.

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Flask](https://img.shields.io/badge/flask-v2.3+-green.svg)
![SQLite](https://img.shields.io/badge/sqlite-v3.0+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

### 🔐 User Management & Security
- **Role-based access control** (Admin/User permissions)
- **Secure authentication** with password hashing and salt
- **Session management** with automatic timeouts
- **Account security** (failed login tracking, temporary locking)
- **Profile management** for users

### 📊 Financial Management
- **Vouchers Payable (VP)** - Track payment obligations
- **Check Vouchers (CV)** - Manage actual payments  
- **Bank Memos** - Record bank transactions *(Coming Soon)*
- **Purchase Orders (PO)** - Handle procurement *(Coming Soon)*

### 🏢 Account Code System
- **Structured coding**: `{BusinessType}-{CompanyID}{SubCode}`
- **B2B accounts** (201) and **B2C accounts** (101)
- **Subcodes** for transaction categorization (-10, -11, -20, etc.)
- **Company management** with business type classification

### 📈 Dashboard & Analytics
- **Real-time statistics** and financial summaries
- **User activity tracking** and recent actions
- **Company-wise breakdowns** and performance metrics
- **Interactive charts** with Chart.js integration

### 🔍 Audit & Compliance
- **Comprehensive audit logging** of all system actions
- **User activity tracking** with IP addresses and timestamps
- **Data change history** (before/after values)
- **Export capabilities** (JSON/CSV formats)

### 🎯 Smart Features
- **First-time setup wizard** for new installations
- **Smart routing** based on user roles and system state
- **Real-time form validation** with AJAX
- **Responsive design** that works on all devices

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Flask 2.3+
- Modern web browser

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

3. **Run the application:**
```bash
python app.py
```

4. **Access the system:**
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
│
├── core/                           # Core system components
│   ├── database.py                 # Database manager
│   ├── logger.py                   # Logging configuration
│   └── security.py                 # Security utilities
│
├── models/                         # Database models
│   ├── user.py                     # User data model
│   └── company.py                  # Company model (coming soon)
│
├── services/                       # Business logic
│   ├── user_service.py            # User management
│   ├── company_service.py         # Company management
│   ├── dashboard_service.py       # Analytics & dashboard
│   └── audit_service.py           # Audit logging
│
├── routes/                         # Flask blueprints
│   ├── auth.py                    # Authentication routes
│   ├── users.py                   # User management routes
│   └── dashboard.py               # Dashboard routes
│
├── templates/                      # HTML templates
│   ├── base.html                  # Base template
│   ├── auth/                      # Login/logout pages
│   ├── users/                     # User management UI
│   └── dashboard/                 # Dashboard UI
│
├── utils/                         # Utilities
│   └── decorators.py             # Custom decorators
│
└── migrations/                    # Database setup
    └── init_db.py                # Database initialization
```

## 💻 Usage

### Admin Features
- **User Management**: Create, edit, delete, and manage user accounts
- **System Configuration**: Set up companies and account codes
- **Full Access**: View all data and system-wide statistics
- **Audit Logs**: Monitor all system activities

### User Features  
- **Profile Management**: Update personal information and passwords
- **Voucher Creation**: Create and manage vouchers (coming soon)
- **Dashboard Access**: View personal statistics and recent activities

### Account Code Format
The system uses a structured account coding system:
- **Format**: `{BusinessType}-{CompanyID}{SubCode}`
- **Example**: `201-UMT01-10`
  - `201` = B2B business type
  - `UMT01` = Company identifier
  - `-10` = General expenses subcode

## 🔧 Development

### Running in Development Mode
```bash
# Enable debug mode
export FLASK_ENV=development
python app.py
```

### Database Management
```bash
# Reset database (WARNING: Deletes all data)
python migrations/init_db.py

# Check system status
python troubleshoot.py
```

### Testing Login Issues
```bash
# Debug login problems
python debug_login.py

# Quick fix for admin user
python simple_fix.py
```

## 🛠️ Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite (with planned PostgreSQL support)
- **Frontend**: Bootstrap 5, HTML5, JavaScript
- **Charts**: Chart.js for data visualization
- **Icons**: Font Awesome
- **Security**: Password hashing with salt, session management

## 📋 Roadmap

### Phase 1: Foundation ✅
- [x] User authentication and authorization
- [x] Role-based access control
- [x] Basic dashboard and user management
- [x] Audit logging system

### Phase 2: Core Features (In Progress)
- [ ] Complete voucher management (VP/CV)
- [ ] Company management system
- [ ] Bank memo functionality
- [ ] Purchase order management

### Phase 3: Advanced Features (Planned)
- [ ] Email notifications
- [ ] Document attachments
- [ ] Approval workflows
- [ ] Advanced reporting
- [ ] Multi-currency support
- [ ] API endpoints

### Phase 4: Enterprise Features (Future)
- [ ] Multi-tenant support
- [ ] LDAP/SSO integration
- [ ] Advanced analytics
- [ ] Mobile app
- [ ] Cloud deployment options

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues:

1. **Check the troubleshooting script**: `python troubleshoot.py`
2. **Review the logs**: Check files in the `logs/` directory
3. **Common solutions**: See the [troubleshooting guide](docs/troubleshooting.md)
4. **Create an issue**: [GitHub Issues](https://github.com/YOUR_USERNAME/financial-voucher-system/issues)

## 📊 Screenshots

### Login Page
![Login Page](docs/screenshots/login.png)

### User Management
![User Management](docs/screenshots/user-management.png)

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

---

**Built by Leonard**