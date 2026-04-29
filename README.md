# Rental Girlfriend Platform

A web-based platform for managing companion rental services, including booking, profile management, and admin dashboards.

## Features

- **User Roles**: Separate dashboards for Customers, Companions, and Administrators.
- **Booking System**: Real-time availability and booking flows.
- **Profile Management**: Detailed companion profiles with bios, galleries, and reviews.
- **KHQR Integration**: Seamless payment processing using KHQR.
- **Localization**: Support for multiple languages (English/Khmer).

## Getting Started

### Prerequisites

- Python 3.10+
- Flask

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/rentalGirlfriend.git
    cd rentalGirlfriend
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**:
    Copy `.env.example` to `.env` and fill in your configuration:
    ```bash
    cp .env.example .env
    ```

5.  **Initialize the database**:
    ```bash
    flask db upgrade
    python scripts/seed_roles.py
    python scripts/seed_permissions.py
    python scripts/seed_data.py
    ```

6.  **Run the application**:
    ```bash
    flask run --debug
    ```

## Project Structure

- `app.py`: Application entry point and configuration.
- `models/`: Database models (SQLAlchemy).
- `route/`: Flask blueprints and route definitions.
    - `admin/`: Administrative dashboard routes (Analytics, Bookings, Companions, Customers, Notifications, Payments, Reports, Reviews, Roles, Settings, Users).
    - `front/`: Customer and public-facing routes.
- `templates/`: HTML templates (Jinja2) for both Admin and Front-end.
- `static/`: CSS, JS, and image assets.
- `translations/`: Localization files for Internationalization (English/Khmer).
- `scripts/`: Diagnostic and maintenance scripts.

## Advanced Features

### Role-Based Access Control (RBAC)
The platform uses a comprehensive RBAC system with permissions for every major action (e.g., `companion:verify`, `user:edit`, `booking:manage`). Roles and permissions can be managed from the Admin Dashboard.

### KHQR Payment Integration
Integrated with KHQR for seamless local payment processing. Configuration for merchant IDs and API keys is managed via environment variables in the `.env` file.

## Production Deployment

1.  **Set `FLASK_DEBUG=False`** in your `.env` file.
2.  **Use a production WSGI server** like Gunicorn:
    ```bash
    gunicorn -w 4 -b 0.0.0.0:8000 app:app
    ```
3.  **Ensure volume persistence** for the SQLite database (`mydb.db`) and user uploads (`static/uploads`).

## License

MIT
