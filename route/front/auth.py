from app import app, render_template, redirect, url_for
from werkzeug.security import check_password_hash
from flask import flash, request, session
from models import User
from models.companion_profiles import CompanionProfile
from models.customer_profiles import CustomerProfile
@app.get('/login')
def login():
    # Route unauthenticated users to the right portal based on where they came from
    referrer = request.referrer or ''
    if '/admin' in referrer:
        return redirect(url_for('admin_login'))
    return redirect(url_for('customer_login'))


@app.get('/customer_login')
def customer_login():
    return render_template('front/customer_login.html')


@app.get('/companion_login')
def companion_login():
    return render_template('front/companion_login.html')


@app.get('/admin/login')
def admin_login():
    return render_template('admin/login.html')


@app.get('/logout')
def logout():
    # Check role before clearing session to redirect correctly
    login_url = url_for('customer_login')
    if session.get('user_id'):
        from models import User
        user = User.query.get(session.get('user_id'))
        if user and user.role:
            role_name = user.role.role_name.lower()
            if role_name not in ['customer', 'companion']:
                login_url = url_for('admin_login')
            elif role_name == 'companion':
                login_url = url_for('companion_login')
            
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(login_url)


@app.post('/do_customer_login')
def do_customer_login():
    """Handles login for Customer and Companion roles."""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        role_name = user.role.role_name.lower() if user.role else ''

        # Block admins from using this form
        # Block any role that is not Customer or Companion from this form
        if role_name not in ['customer', 'companion']:
            flash('Please use the Admin login portal.', 'warning')
            return redirect(url_for('admin_login'))

        session['user_id'] = user.user_id
        session.permanent = True

        companion = CompanionProfile.query.filter_by(user_id=user.user_id).first()
        customer = CustomerProfile.query.filter_by(user_id=user.user_id).first()

        flash('Welcome back! You are now logged in.', 'success')
        if companion:
            return redirect(url_for('dashboard_companion'))
        elif customer:
            return redirect(url_for('dashboard_customer'))
        else:
            flash('Profile not found. Please complete your registration.', 'warning')
            return redirect(url_for('register'))
    else:
        flash('Invalid email or password.', 'danger')
        return redirect(request.referrer or url_for('customer_login'))


@app.post('/do_admin_login')
def do_admin_login():
    """Handles login exclusively for Admin role."""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        role_name = user.role.role_name.lower() if user.role else ''

        # Only allow admins
        # Only allow non-Customer and non-Companion roles
        if role_name in ['customer', 'companion']:
            flash('Access denied. This portal is for administrators and staff only.', 'danger')
            return redirect(url_for('admin_login'))

        session['user_id'] = user.user_id
        session.permanent = True
        flash('Welcome to the Admin Dashboard!', 'success')
        return redirect(url_for('admin_home'))
    else:
        flash('Invalid email or password.', 'danger')
        return redirect(url_for('admin_login'))



@app.get('/register')
def register():
    return render_template('front/register.html')

@app.get('/register-customer')
def register_customer():
    return render_template('front/register-customer.html')

@app.get('/register-companion')
def register_companion():
    return render_template('front/register-companion.html')

@app.get('/forgot-password')
def forgot_password():
    return render_template('front/forgot-password.html')

@app.get('/registration-success')
def registration_success():
    return render_template('front/registration-success.html')

