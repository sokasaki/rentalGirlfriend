from app import app, render_template, request, redirect, url_for, flash, admin_required, permission_required
from extensions import db
from models import Role, AuditLog, Permission
from flask import session

@app.route('/admin/roles', methods=['GET'])
@admin_required
@permission_required('manage_roles')
def roles():
    all_roles = Role.query.all()
    all_permissions = Permission.query.all()
    from models import CompanionProfile
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    return render_template(
        'admin/roles.html', 
        active_page='roles', 
        roles=all_roles, 
        permissions=all_permissions,
        pending_count=pending_count
    )

@app.route('/admin/roles/add', methods=['POST'])
@admin_required
@permission_required('manage_roles')
def add_role():
    role_name = request.form.get('role_name')
    if not role_name:
        flash('Role name is required!', 'error')
        return redirect(url_for('roles'))
    
    # Check if role already exists
    existing = Role.query.filter_by(role_name=role_name).first()
    if existing:
        flash(f'Role "{role_name}" already exists!', 'warning')
        return redirect(url_for('roles'))
    
    try:
        new_role = Role(role_name=role_name)
        
        # Add selected permissions
        permission_ids = request.form.getlist('permissions')
        if permission_ids:
            perms = Permission.query.filter(Permission.permission_id.in_(permission_ids)).all()
            new_role.permissions.extend(perms)
            
        db.session.add(new_role)
        db.session.commit()
        
        AuditLog.log(
            user_id=session.get('user_id'),
            action='ADD_ROLE',
            details=f"Added new role: {role_name}",
            ip_address=request.remote_addr
        )
        
        flash(f'Role "{role_name}" added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding role: {str(e)}', 'error')
        
    return redirect(url_for('roles'))

@app.route('/admin/roles/edit/<int:role_id>', methods=['POST'])
@admin_required
@permission_required('manage_roles')
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    new_name = request.form.get('role_name')
    
    # Protect core roles from being renamed
    if role.role_name in ['Admin', 'Customer', 'Companion']:
        flash(f'Core role "{role.role_name}" cannot be renamed.', 'error')
        return redirect(url_for('roles'))
        
    if not new_name:
        flash('Role name cannot be empty!', 'error')
        return redirect(url_for('roles'))
    
    try:
        old_name = role.role_name
        role.role_name = new_name
        
        # Update permissions
        permission_ids = request.form.getlist('permissions')
        perms = Permission.query.filter(Permission.permission_id.in_(permission_ids)).all()
        role.permissions = perms
        
        db.session.commit()
        
        AuditLog.log(
            user_id=session.get('user_id'),
            action='EDIT_ROLE',
            details=f"Renamed role from {old_name} to {new_name}",
            ip_address=request.remote_addr
        )
        
        flash('Role updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating role: {str(e)}', 'error')
        
    return redirect(url_for('roles'))

@app.route('/admin/roles/delete/<int:role_id>', methods=['POST'])
@admin_required
@permission_required('manage_roles')
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    # Protect core roles from deletion
    if role.role_name in ['Admin', 'Customer', 'Companion']:
        flash(f'Core role "{role.role_name}" cannot be deleted!', 'error')
        return redirect(url_for('roles'))
    
    # Check if users are assigned to this role
    if role.users:
        flash(f'Cannot delete role "{role.role_name}" because it is currently assigned to {len(role.users)} users.', 'warning')
        return redirect(url_for('roles'))
        
    try:
        role_name = role.role_name
        db.session.delete(role)
        db.session.commit()
        
        AuditLog.log(
            user_id=session.get('user_id'),
            action='DELETE_ROLE',
            details=f"Deleted role: {role_name}",
            ip_address=request.remote_addr
        )
        
        flash(f'Role "{role_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting role: {str(e)}', 'error')
        
    return redirect(url_for('roles'))
