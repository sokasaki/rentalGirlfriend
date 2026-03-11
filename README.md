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
    python seed_data.py
    ```

6.  **Run the application**:
    ```bash
    flask run --debug
    ```

## Project Structure

- `app.py`: Application entry point.
- `models/`: Database models.
- `route/`: Flask blueprints and route definitions.
- `templates/`: HTML templates (Jinja2).
- `static/`: CSS, JS, and image assets.
- `translations/`: Localization files.

## License

MIT
