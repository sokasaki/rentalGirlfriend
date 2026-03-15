from app import app, render_template, request, redirect, url_for, flash, admin_required, permission_required
from models import SystemSetting, AuditLog
from flask import session

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
@permission_required('setting:view')
def settings():
    if request.method == 'POST':
        platform_name = request.form.get('platform_name')
        platform_fee = request.form.get('platform_fee')
        
        if platform_name:
            SystemSetting.set_value('platform_name', platform_name, "Name of the platform")
        if platform_fee:
            SystemSetting.set_value('platform_fee', platform_fee, "Platform commission percentage")
            
        # Log action
        AuditLog.log(
            user_id=session.get('user_id'),
            action='UPDATE_SETTINGS',
            details=f"Updated platform settings: name={platform_name}, fee={platform_fee}",
            ip_address=request.remote_addr
        )
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))

    from models import CompanionProfile
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    
    platform_name = SystemSetting.get_value('platform_name', 'RentACompanion')
    platform_fee = SystemSetting.get_value('platform_fee', '15')
    
    return render_template(
        'admin/settings.html', 
        active_page='settings', 
        pending_count=pending_count,
        platform_name=platform_name,
        platform_fee=platform_fee
    )