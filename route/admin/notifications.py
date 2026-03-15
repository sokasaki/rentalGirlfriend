from app import app, render_template, request, db, flash, redirect, url_for, admin_required, permission_required
from models import User, Role, Notification, AuditLog, RoleEnum
from flask import session
from datetime import datetime

@app.get('/admin/broadcast')
@admin_required
@permission_required('broadcast:send')
def broadcast_page():
    # Get pending count for sidebar
    from models import CompanionProfile as CP
    pending_count = CP.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/broadcast.html',
        active_page='broadcast',
        pending_count=pending_count
    )

@app.post('/admin/broadcast/send')
@admin_required
@permission_required('broadcast:send')
def send_broadcast():
    title = request.form.get('title')
    message = request.form.get('message')
    target = request.form.get('target', 'all') # 'all', 'customers', 'companions'
    
    if not title or not message:
        flash('Title and message are required', 'error')
        return redirect(url_for('broadcast_page'))
        
    query = User.query.join(Role)
    if target == 'customers':
        query = query.filter(Role.role_name == "Customer")
    elif target == 'companions':
        query = query.filter(Role.role_name == "Companion")
    elif target == 'all':
        query = query.filter(Role.role_name != "Admin")
        
    users = query.all()
    
    for user in users:
        notification = Notification(
            user_id=user.user_id,
            title=title,
            message=message,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        
    db.session.commit()
    
    # Log action
    AuditLog.log(
        user_id=session.get('user_id'),
        action='SEND_BROADCAST',
        details=f"Sent broadcast '{title}' to {target} users ({len(users)} users)",
        ip_address=request.remote_addr
    )
    
    flash(f"Broadcast sent successfully to {len(users)} users!", "success")
    return redirect(url_for('broadcast_page'))
