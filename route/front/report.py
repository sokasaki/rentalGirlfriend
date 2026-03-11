from flask import session, redirect, url_for, request, flash, jsonify
from app import app, db, render_template
from models.reports import Report, TargetTypeEnum, ReportStatusEnum
from datetime import datetime

@app.post('/submit_report')
def submit_report():
    user_id = session.get('user_id')
    if not user_id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Login required'}), 401
        flash('You must be logged in to submit a report.', 'error')
        return redirect(url_for('login'))
        
    if request.is_json:
        data = request.get_json()
        target_type = data.get('target_type')
        target_id = data.get('target_id')
        full_reason = data.get('reason')
    else:
        target_type = request.form.get('target_type')
        target_id = request.form.get('target_id')
        reason_select = request.form.get('reason')
        details = request.form.get('details', '').strip()
        
        # Debug: log what we received
        print(f"[submit_report] target_type={target_type!r}, target_id={target_id!r}, reason={reason_select!r}")
        
        missing = []
        if not target_type:  missing.append('target_type')
        if not target_id:    missing.append('target_id')
        if not reason_select: missing.append('reason (select a reason card)')
        
        if missing:
            flash(f'Missing fields: {", ".join(missing)}', 'error')
            return redirect(request.referrer or url_for('home'))
            
        full_reason = f"[{reason_select}]"
        if details:
            full_reason += f" {details}"
        
    if not all([target_type, target_id, full_reason]):
        if request.is_json:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        flash('All fields are required.', 'error')
        return redirect(request.referrer or url_for('home'))

        
    try:
        report = Report(
            reporter_id=user_id,
            target_type=TargetTypeEnum[target_type.upper()],
            target_id=int(target_id),
            reason=full_reason,
            status=ReportStatusEnum.PENDING,
            created_at=datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Report submitted successfully'})
            
        flash('Your report has been submitted successfully and will be reviewed by our team.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'An error occurred while submitting your report: {str(e)}', 'error')
        
    return redirect(request.referrer or url_for('home'))

@app.post('/respond_to_report/<int:report_id>')
def respond_to_report(report_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401
        
    report = Report.query.get_or_404(report_id)
    
    # Allow the TARGET user to respond (the one who was reported and notified)
    # target_id is now always the user_id for COMPANION and USER types
    from models.reports import TargetTypeEnum
    is_target = (
        report.target_type in (TargetTypeEnum.COMPANION, TargetTypeEnum.USER)
        and report.target_id == user_id
    )
    is_reporter = (report.reporter_id == user_id)

    if not is_target and not is_reporter:
        flash('You are not authorized to respond to this report.', 'error')
        return redirect(request.referrer or url_for('home'))
        
    details = request.form.get('details', '').strip()
    if not details:
        flash('Please provide the requested information.', 'error')
        return redirect(request.referrer or url_for('home'))
        
    try:
        # Append response to existing reason
        report.reason += f"\n\n[USER RESPONSE]: {details}"
        report.status = ReportStatusEnum.PENDING
        report.info_requested_at = None
        
        db.session.commit()
        flash('Information submitted successfully. Thank you.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
        
    # Redirect target back to their appropriate dashboard
    from models.companion_profiles import CompanionProfile
    companion = CompanionProfile.query.filter_by(user_id=user_id).first()
    if companion:
        return redirect(url_for('dashboard_companion'))
    return redirect(url_for('dashboard_customer'))

