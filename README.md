# SokoHub — E-Commerce Platform

SokoHub is a modern, full-stack e-commerce platform built with Django and designed for a scalable online shopping experience.

The platform provides a complete shopping workflow — from product discovery and cart management to checkout, customer information, and M-Pesa payment processing — while maintaining a clean, maintainable Django architecture.

---

## Overview

SokoHub is built as a **Django monolithic application**, keeping the core business logic, database operations, authentication, shopping workflow, and payment integration within a single application.

The project focuses on building a practical e-commerce system with a strong backend foundation and room for future expansion.

### Core capabilities

- Product catalog and product management
- Category-based product organization
- Product images and detailed product pages
- Customer authentication and account management
- Shopping cart functionality
- Checkout workflow
- Customer billing and shipping information
- M-Pesa payment integration
- Order processing
- Newsletter subscription functionality
- Responsive e-commerce interface
- Docker-based development and deployment support
- Environment-based configuration for sensitive credentials

---

## Architecture

SokoHub follows a modular Django architecture designed to keep responsibilities separated while maintaining the simplicity of a monolithic application.

```text
SokoHub
│
├── Django Project
│   ├── Settings
│   ├── URL Configuration
│   ├── WSGI / ASGI
│   └── Application Configuration
│
├── Store
│   ├── Products
│   ├── Categories
│   ├── Cart
│   ├── Orders
│   └── Store Views
│
├── Accounts
│   ├── Authentication
│   ├── User Profiles
│   └── Customer Information
│
├── Payments
│   ├── M-Pesa Integration
│   ├── Payment Requests
│   └── Payment Status
│
├── Templates
│   ├── Store Interface
│   ├── Checkout
│   └── Customer Pages
│
├── Static
│   ├── CSS
│   ├── JavaScript
│   └── Images
│
└── Docker
    ├── Dockerfile
    └── Docker Compose
```

The architecture can evolve into separate services if the application's scale eventually requires it.

---

## Technology Stack

### Backend

- **Python**
- **Django**
- Django ORM
- Django Authentication
- Django Templates

### Database

- Relational database architecture
- Django ORM for database abstraction

### Payments

- **M-Pesa**
- Payment request processing
- Transaction status handling

### Frontend

- HTML5
- CSS3
- JavaScript
- Django Template Language

### Infrastructure

- Docker
- Docker Compose
- Gunicorn
- Environment variables

### Development Tools

- Git
- GitHub
- Python virtual environments

---

## Application Flow

The primary customer journey follows a standard e-commerce workflow:

```text
Browse Products
      │
      ▼
Product Details
      │
      ▼
Add to Cart
      │
      ▼
Review Cart
      │
      ▼
Checkout
      │
      ▼
Billing / Shipping Information
      │
      ▼
M-Pesa Payment
      │
      ▼
Payment Verification
      │
      ▼
Order Processing
```

This workflow keeps the customer experience straightforward while allowing the backend to handle the underlying business logic.

---

## M-Pesa Payments

SokoHub integrates M-Pesa into the checkout process to support mobile payments.

The payment workflow is designed around:

1. Customer initiates checkout.
2. Customer provides the required payment information.
3. SokoHub creates a payment request.
4. The customer authorizes the transaction through M-Pesa.
5. The application processes the payment response.
6. Payment status is recorded.
7. The order can proceed based on the transaction result.

Payment credentials and sensitive configuration should be supplied through environment variables rather than committed to source control.

---

## Security

Security is treated as a core application concern.

The project uses Django's built-in security mechanisms together with environment-based configuration.

Key practices include:

- Secret keys stored outside source control
- Environment variables for API credentials
- CSRF protection
- Django authentication and session management
- Password hashing through Django
- Server-side validation
- Controlled database access through Django ORM
- Sensitive files excluded through `.gitignore`
- Docker-specific files excluded through `.dockerignore`

> Never commit production credentials, API keys, M-Pesa secrets, database passwords, or `.env` files to GitHub.

---

## Project Structure

A simplified project structure:

```text
Ecommerce/
│
├── ecom/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── store/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── templates/
│
├── payment/
│   ├── models.py
│   ├── views.py
│   └── payment.py
│
├── templates/
│
├── static/
│
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yaml
├── .dockerignore
├── .gitignore
└── README.md
```

The exact structure may evolve as the application continues to develop.

---

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/mauricekabubu/SokoHub.git
cd SokoHub
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file and provide the required application configuration.

Example:

```env
SECRET_KEY=your-secret-key
DEBUG=True

DATABASE_URL=your-database-url

MPESA_CONSUMER_KEY=your-consumer-key
MPESA_CONSUMER_SECRET=your-consumer-secret
MPESA_SHORTCODE=your-shortcode
MPESA_PASSKEY=your-passkey
```

Do not commit `.env` to Git.

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create an administrator

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The application will be available locally through the Django development server.

---

## Docker

SokoHub includes Docker configuration to make the application easier to run in a consistent environment.

Build and start the services:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d
```

Stop the services:

```bash
docker compose down
```

---

## Database Migrations

Whenever database models are modified:

```bash
python manage.py makemigrations
python manage.py migrate
```

For production deployments, migrations should be reviewed and applied as part of the deployment process.

---

## Development Workflow

The project follows a feature-oriented Git workflow.

Example:

```bash
git switch -c feature/payment-improvements

git add .
git commit -m "feat: improve M-Pesa payment processing"

git push -u origin feature/payment-improvements
```

Commit messages follow the **Conventional Commits** style where practical:

```text
feat:     New functionality
fix:      Bug fixes
refactor: Code restructuring
chore:    Maintenance/configuration
docs:     Documentation
test:     Tests
```

---

## Current Development Status

SokoHub is an actively developed project.

### Implemented

- [x] Django project foundation
- [x] Product/store functionality
- [x] Customer authentication
- [x] Shopping cart
- [x] Checkout workflow
- [x] Billing information
- [x] M-Pesa payment integration
- [x] Docker configuration
- [x] Environment-based configuration
- [x] Newsletter functionality

### In Development

- [ ] Comprehensive automated test suite
- [ ] Production payment hardening
- [ ] Advanced order management
- [ ] Improved customer account dashboard
- [ ] Production deployment optimization
- [ ] Monitoring and logging
- [ ] Performance optimization

---

## Future Roadmap

The architecture is intentionally designed to support additional functionality.

Potential future improvements include:

- Advanced product search
- Product filtering and sorting
- Inventory management
- Order tracking
- Customer reviews and ratings
- Wishlist functionality
- Discount and coupon system
- Improved payment reconciliation
- Email notification workflows
- Admin analytics dashboard
- REST API layer
- Automated testing and CI/CD
- Cloud deployment
- Observability and application monitoring

---

## Engineering Principles

SokoHub development focuses on:

**Maintainability**  
Code should remain understandable and easy to modify as the platform grows.

**Security**  
Sensitive credentials and application secrets should never be exposed through source control.

**Separation of concerns**  
Business logic, presentation, data access, and integrations should have clear responsibilities.

**Scalability**  
The application should be capable of evolving from a simple monolith into a more distributed architecture when justified by actual requirements.

**Developer experience**  
Docker, environment configuration, Git conventions, and clear project structure are used to make development reproducible.

---

## Contributing

Contributions and improvements are welcome.

A typical contribution workflow:

```bash
git clone https://github.com/mauricekabubu/SokoHub.git

git switch -c feature/your-feature

git add .

git commit -m "feat: describe your change"

git push -u origin feature/your-feature
```

Open a pull request with a clear description of:

- What changed
- Why the change was necessary
- How it was tested
- Any configuration changes required

---

## License

This project is currently maintained as a private/development project.

License information will be added when the project's distribution terms are finalized.

---

## Author

**Maurice Kabubu**

Computer Science student and software developer focused on backend engineering, cloud technologies, and intelligent software systems.

GitHub: `@mauricekabubu`

---

## Project Status

**SokoHub — Active Development**

Built with Django, Python, and a focus on creating a maintainable, production-oriented e-commerce platform.
