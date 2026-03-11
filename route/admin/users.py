from app import app, render_template, request, redirect, url_for, flash, admin_required, permission_required
from extensions import db
from models import User, Role
from werkzeug.security import generate_password_hash

@app.get('/admin/users')
@admin_required
@permission_required('manage_users')
def users():
    from models import CompanionProfile
    
    # Get query parameters for search and filter
    search_query = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    
    # Build query
    query = User.query.join(Role)
    
    # Apply search filter (email or phone)
    if search_query:
        query = query.filter(
            (User.email.ilike(f'%{search_query}%')) |
            (User.phone.ilike(f'%{search_query}%'))
        )
    
    # Apply role filter (convert to int if provided)
    if role_filter:
        try:
            role_filter = int(role_filter)
            query = query.filter(User.role_id == role_filter)
        except ValueError:
            pass
    
    all_users = query.all()
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    
    # Get all roles for filter dropdown
    roles = Role.query.all()
    
    return render_template(
        'admin/users.html', 
        active_page='users', 
        users=all_users, 
        pending_count=pending_count,
        search_query=search_query,
        role_filter=role_filter,
        roles=roles
    )

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
@permission_required('manage_users')
def add_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        role_id = request.form.get('role_id')
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # Create new user
        new_user = User(
            email=email,
            password=hashed_password,
            phone=phone,
            role_id=role_id
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('User added successfully!', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {str(e)}', 'error')
    
    roles = Role.query.all()
    from models import CompanionProfile
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    return render_template('admin/user/addUser.html', active_page='users', roles=roles, pending_count=pending_count)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
@permission_required('manage_users')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.role_id = request.form.get('role_id')
        
        # Update password only if provided
        password = request.form.get('password')
        if password:
            user.password = generate_password_hash(password)
        
        try:
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    roles = Role.query.all()
    from models import CompanionProfile
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    return render_template('admin/user/editUser.html', active_page='users', user=user, roles=roles, pending_count=pending_count)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
@permission_required('manage_users')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('users'))


