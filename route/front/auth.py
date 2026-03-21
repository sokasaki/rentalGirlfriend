from app import app, render_template, redirect, url_for, db
from werkzeug.security import check_password_hash, generate_password_hash
from flask import flash, request, session
from models import User, Role, RoleEnum
from models.companion_profiles import CompanionProfile, CompanionGenderEnum
from models.customer_profiles import CustomerProfile, GenderEnum
from models.companion_photos import CompanionPhoto
from upload_service import save_image
from datetime import datetime
import os
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



@app.post('/do_register_customer')
def do_register_customer():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    dob_str = request.form.get('dob')
    gender_str = request.form.get('gender')
    location = request.form.get('location')
    bio = request.form.get('bio')

    # Basic Validation
    if not all([full_name, email, password, dob_str, gender_str]):
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('register_customer'))

    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('register_customer'))

    if User.query.filter_by(email=email).first():
        flash('Email already registered.', 'danger')
        return redirect(url_for('register_customer'))

    try:
        # Create User
        customer_role = Role.query.filter_by(role_name=RoleEnum.CUSTOMER.value).first()
        if not customer_role:
            flash('System error: Customer role not found.', 'danger')
            return redirect(url_for('register_customer'))

        new_user = User(
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            role_id=customer_role.role_id
        )
        db.session.add(new_user)
        db.session.flush()

        # Handle Profile Photo
        profile_photo_path = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename != '':
                upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'profiles')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                upload_result = save_image(file, upload_folder, allowed_extensions)
                if isinstance(upload_result, dict):
                    profile_photo_path = f"uploads/profiles/{upload_result['original']}"

        # Create Customer Profile
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        new_profile = CustomerProfile(
            user_id=new_user.user_id,
            full_name=full_name,
            date_of_birth=dob,
            gender=GenderEnum[gender_str],
            location=location,
            bio=bio,
            profile_photo=profile_photo_path
        )
        db.session.add(new_profile)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('registration_success', type='customer'))

    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('register_customer'))


@app.post('/do_register_companion')
def do_register_companion():
    display_name = request.form.get('display_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    dob_str = request.form.get('dob')
    age = request.form.get('age')
    gender_str = request.form.get('gender')
    location = request.form.get('location')
    rate_per_hour = request.form.get('rate_per_hour')
    bio = request.form.get('bio')
    
    languages = request.form.getlist('languages')
    traits = request.form.getlist('traits')
    available_days = request.form.getlist('available_days')

    # Basic Validation
    if not all([display_name, email, password, dob_str, age, gender_str, rate_per_hour]):
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('register_companion'))

    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('register_companion'))

    if User.query.filter_by(email=email).first():
        flash('Email already registered.', 'danger')
        return redirect(url_for('register_companion'))

    try:
        # Create User
        companion_role = Role.query.filter_by(role_name=RoleEnum.COMPANION.value).first()
        if not companion_role:
            flash('System error: Companion role not found.', 'danger')
            return redirect(url_for('register_companion'))

        new_user = User(
            email=email,
            password=generate_password_hash(password),
            phone=phone,
            role_id=companion_role.role_id
        )
        db.session.add(new_user)
        db.session.flush()

        # Create Companion Profile
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        new_profile = CompanionProfile(
            user_id=new_user.user_id,
            display_name=display_name,
            date_of_birth=dob,
            age=int(age),
            gender=CompanionGenderEnum[gender_str],
            location=location,
            rate_per_hour=float(rate_per_hour),
            bio=bio,
            languages=languages,
            personality_traits=traits
        )
        db.session.add(new_profile)
        db.session.flush()

        # Handle Multiple Profile Photos
        if 'profile_photos' in request.files:
            files = request.files.getlist('profile_photos')
            upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'companions')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            for i, file in enumerate(files):
                if file and file.filename != '':
                    upload_result = save_image(file, upload_folder, allowed_extensions)
                    if isinstance(upload_result, dict):
                        new_photo = CompanionPhoto(
                            companion_id=new_profile.companion_id,
                            photo_url=f"uploads/companions/{upload_result['original']}",
                            is_primary=(i == 0)
                        )
                        db.session.add(new_photo)

        db.session.commit()

        flash('Registration successful! Your profile is under review.', 'success')
        return redirect(url_for('registration_success', type='companion'))

    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('register_companion'))


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

