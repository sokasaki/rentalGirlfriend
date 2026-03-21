import sys
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from extensions import db, migrate

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('admin_login'))
        
        from models.users import User
        user = User.query.get(session.get('user_id'))
        if not user or not user.role:
            return redirect(url_for('admin_login'))
            
        role_name = user.role.role_name.lower()
        if role_name in ['customer', 'companion']:
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('admin_login'))
            
            from models.users import User
            user = User.query.get(session.get('user_id'))
            if not user or not user.role:
                return redirect(url_for('admin_login'))
                
            # Allow Admin to access everything by default, or check specific permission
            if user.role.role_name == 'Admin' or user.role.has_permission(permission_name):
                return f(*args, **kwargs)
                
            flash(f'Access denied. You do not have permission to {permission_name.replace("_", " ")}.', 'danger')
            return redirect(url_for('admin_home'))
        return decorated_function
    return decorator

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

app = Flask(__name__)

if load_dotenv:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(env_path)


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///mydb.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
app.config["PERMANENT_SESSION_LIFETIME"] = int(os.getenv("PERMANENT_SESSION_LIFETIME", "2592000"))  # 30 days
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = _env_bool("SESSION_COOKIE_SECURE", False)
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

# Stripe Configuration
app.config["STRIPE_PUBLIC_KEY"] = os.getenv("STRIPE_PUBLIC_KEY", "")
app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY", "")

# KHQR (Bakong) Configuration - Optional QR code payment service
app.config["KHQR_ENABLED"] = _env_bool("KHQR_ENABLED", True)
app.config["KHQR_TOKEN"] = os.getenv("KHQR_TOKEN", "").strip().strip('"\'')
app.config["KHQR_BANK_ACCOUNT"] = os.getenv("KHQR_BANK_ACCOUNT", "nol_piseth@bkrt")
app.config["KHQR_MERCHANT_NAME"] = os.getenv("KHQR_MERCHANT_NAME", "RentACompanion Co.")
app.config["KHQR_MERCHANT_CITY"] = os.getenv("KHQR_MERCHANT_CITY", "Phnom Penh")
app.config["KHQR_PHONE_NUMBER"] = os.getenv("KHQR_PHONE_NUMBER", "")
app.config["KHQR_STORE_LABEL"] = os.getenv("KHQR_STORE_LABEL", "RentACompanion")
app.config["KHQR_TERMINAL_LABEL"] = os.getenv("KHQR_TERMINAL_LABEL", "Cashier-01")
app.config["KHQR_CURRENCY"] = os.getenv("KHQR_CURRENCY", "KHR")
app.config["KHQR_EXCHANGE_RATE"] = int(os.getenv("KHQR_EXCHANGE_RATE", "4100"))
app.config["FLASK_DEBUG"] = _env_bool("FLASK_DEBUG", True)

db.init_app(app)
migrate.init_app(app, db)

from models import *

# Template context processor to make user_type available globally
@app.context_processor
def inject_user_type():
    user_type = None
    is_admin = False
    notification_count = 0
    pending_bookings = []
    approved_bookings = []
    current_user = None
    platform_name = 'RentACompanion'
    platform_fee = '15'
    
    def has_perm(permission_name):
        user_id = session.get('user_id')
        if not user_id:
            return False
        from models.users import User
        user = User.query.get(user_id)
        if not user or not user.role:
            return False
        if user.role.role_name == 'Admin':
            return True
        return user.role.has_permission(permission_name)

    if session.get('user_id'):
        from models.companion_profiles import CompanionProfile
        from models.customer_profiles import CustomerProfile
        from models.bookings import Booking, BookingStatusEnum
        from models.users import User
        
        user_id = session.get('user_id')
        current_user = User.query.get(user_id)
        
        if current_user and current_user.role:
            role_name = current_user.role.role_name.lower()
            if role_name not in ['customer', 'companion']:
                is_admin = True
            
        companion = CompanionProfile.query.filter_by(user_id=user_id).first()
        customer = CustomerProfile.query.filter_by(user_id=user_id).first()
        
        if companion:
            user_type = 'companion'
            # Count pending booking requests for companion
            pending_bookings_query = Booking.query.filter_by(
                companion_id=companion.companion_id,
                status=BookingStatusEnum.PENDING
            ).all()
            # notification_count will be calculated below after fetching all notification types
            
            # Get booking details for dropdown
            for booking in pending_bookings_query[:5]:  # Limit to 5 most recent
                customer_profile = CustomerProfile.query.get(booking.customer_id)
                pending_bookings.append({
                    'booking_id': booking.booking_id,
                    'customer_name': customer_profile.full_name if customer_profile else 'Anonymous',
                    'start_time': booking.start_time,
                    'amount': float(booking.total_price)
                })
                
        elif customer:
            user_type = 'customer'
            # Count approved bookings waiting for payment
            approved_bookings_query = Booking.query.filter_by(
                customer_id=customer.customer_id,
                status=BookingStatusEnum.APPROVED
            ).all()
            
            # Get booking details for dropdown
            for booking in approved_bookings_query[:5]:  # Limit to 5 most recent
                companion_profile = CompanionProfile.query.get(booking.companion_id)
                approved_bookings.append({
                    'booking_id': booking.booking_id,
                    'companion_name': companion_profile.display_name if companion_profile else 'Unknown',
                    'start_time': booking.start_time,
                    'amount': float(booking.total_price)
                })

        # Fetch unread notifications for any logged in user
        from models.notifications import Notification
        from models.reports import Report, ReportStatusEnum
        
        unread_notifications = Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).order_by(Notification.created_at.desc()).all()
        
        # Pending reports needing attention:
        # - For COMPANIONS: reports filed AGAINST them (they are target_id, type=COMPANION)
        # - For CUSTOMERS: reports they filed that are awaiting info (they are reporter)
        from models.reports import Report, ReportStatusEnum, TargetTypeEnum
        if companion:
            pending_reports = Report.query.filter_by(
                target_id=user_id,
                status=ReportStatusEnum.AWAITING_INFO
            ).filter(
                Report.target_type == TargetTypeEnum.COMPANION
            ).all()
        else:
            pending_reports = Report.query.filter_by(
                reporter_id=user_id,
                status=ReportStatusEnum.AWAITING_INFO
            ).all()
        
        notification_count = len(unread_notifications) + len(pending_bookings) + len(approved_bookings) + len(pending_reports)
        
        from models.settings import SystemSetting
        platform_name = SystemSetting.get_value('platform_name', 'RentACompanion')
        platform_fee = SystemSetting.get_value('platform_fee', '15')

        return dict(
            user_type=user_type,
            notification_count=notification_count,
            pending_bookings=pending_bookings,
            approved_bookings=approved_bookings,
            notifications=unread_notifications,
            pending_reports=pending_reports,
            platform_name=platform_name,
            platform_fee=platform_fee,
            current_user=current_user,
            is_admin=is_admin,
            has_perm=has_perm
        )
    
    from models.settings import SystemSetting
    platform_name = SystemSetting.get_value('platform_name', 'RentACompanion')
    platform_fee = SystemSetting.get_value('platform_fee', '15')

    return dict(
        user_type=None,
        notification_count=0,
        pending_bookings=[],
        approved_bookings=[],
        notifications=[],
        pending_reports=[],
        platform_name=platform_name,
        platform_fee=platform_fee,
        current_user=None,
        has_perm=has_perm
    )

@app.before_request
def check_user_status():
    # Exempt routes
    exempt_routes = ['login', 'admin_login', 'customer_login', 'companion_login',
                     'do_customer_login', 'do_admin_login', 'static', 'logout', 'home']
    if request.endpoint in exempt_routes or not request.endpoint:
        return

    if session.get('user_id'):
        from models.users import User, UserStatus
        from models.reports import Report, ReportStatusEnum
        from datetime import datetime, timedelta
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        # Helper: pick the right login page based on current endpoint
        def _login_redirect():
            endpoint = request.endpoint or ''
            if endpoint.startswith('admin') or request.path.startswith('/admin'):
                return redirect(url_for('admin_login'))
            return redirect(url_for('customer_login'))
        
        if not user:
            session.clear()
            return _login_redirect()
            
        # 1. Check if user is banned or suspended
        if user.status in [UserStatus.BANNED, UserStatus.SUSPENDED]:
            # Check if temporary suspension has expired
            if user.status == UserStatus.SUSPENDED and user.suspended_until:
                if datetime.utcnow() > user.suspended_until:
                    user.status = UserStatus.ACTIVE
                    user.suspended_until = None
                    db.session.commit()
                    return # Continue to next checks (auto-suspension, etc)
            
            status_name = user.status.value.lower()
            session.clear()
            
            error_msg = f'Your account has been {status_name}. Please contact support.'
            if user.status == UserStatus.SUSPENDED and user.suspended_until:
                error_msg = f'Your account is suspended until {user.suspended_until.strftime("%Y-%m-%d %H:%M")} UTC.'
                
            flash(error_msg, 'danger')
            return _login_redirect()
            
        # 2. Check for auto-suspension (1 hour deadline for info request)
        pending_report = Report.query.filter_by(
            reporter_id=user_id, 
            status=ReportStatusEnum.AWAITING_INFO
        ).first()
        
        if pending_report and pending_report.info_requested_at:
            deadline = pending_report.info_requested_at + timedelta(hours=1)
            if datetime.utcnow() > deadline:
                user.status = UserStatus.SUSPENDED
                db.session.commit()
                session.clear()
                flash('Your account has been suspended for failing to provide required information in time (1-hour window).', 'danger')
                return _login_redirect()

# Import routes after models are fully initialized
with app.app_context():
    import route
    from route import khqr_routes


if __name__ == '__main__':
    app.run(debug=app.config["FLASK_DEBUG"])
