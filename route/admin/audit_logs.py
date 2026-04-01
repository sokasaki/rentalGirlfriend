from app import app, render_template, db, admin_required, permission_required
from flask import request
from models.audit_logs import AuditLog
from models.users import User
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from sqlalchemy import desc

@app.route('/admin/audit-logs')
@admin_required
@permission_required('audit_log:view')
def audit_logs():
    # Filters
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    user_id_filter = request.args.get('user_id', type=int)
    
    query = AuditLog.query
    
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    
    if user_id_filter:
        query = query.filter(AuditLog.user_id == user_id_filter)
        
    pagination = query.order_by(desc(AuditLog.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    logs = pagination.items
    
    # Get all unique actions for the filter dropdown
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions]
    
    # Get all admins for the filter dropdown
    admins = User.query.filter(User.role_id == 1).all() # Assuming role_id 1 is Admin
    
    # Required for sidebar
    pending_count = CompanionProfile.query.filter_by(verification_status=VerificationStatusEnum.PENDING).count()
    
    return render_template(
        'admin/audit_logs.html',
        active_page='audit_logs',
        logs=logs,
        pagination=pagination,
        actions=actions,
        admins=admins,
        selected_action=action_filter,
        selected_user_id=user_id_filter,
        pending_count=pending_count
    )
