from app import app, render_template, request, db, flash, redirect, url_for, admin_required, permission_required
from flask import make_response, session
from models import Payment, PaymentStatusEnum, Booking, CustomerProfile, CompanionProfile, SystemSetting, AuditLog
from datetime import datetime
import csv
import io
from sqlalchemy import func

@app.get('/admin/payments')
@admin_required
@permission_required('payment:view')
def payments():
    # Get query parameters for search and filter
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    
    # Calculate financial statistics (always unfiltered)
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatusEnum.PAID
    ).scalar() or 0
    
    # Platform fee from settings (default 15%)
    fee_percentage = float(SystemSetting.get_value('platform_fee', 15))
    platform_fees = float(total_revenue) * (fee_percentage / 100)
    
    total_refunds = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatusEnum.REFUNDED
    ).scalar() or 0
    
    # Count by status
    refunded_count = Payment.query.filter(Payment.status == PaymentStatusEnum.REFUNDED).count()
    failed_payments_count = 0
    
    # Build filtered query
    query = Payment.query
    
    # Apply status filter
    status_enum_map = {
        'COMPLETED': [PaymentStatusEnum.PAID],
        'PENDING': [PaymentStatusEnum.PENDING],
        'FAILED': [PaymentStatusEnum.REFUNDED],
    }
    
    if status_filter and status_filter in status_enum_map:
        query = query.filter(Payment.status.in_(status_enum_map[status_filter]))
    
    # Apply search filter (by customer name or companion name)
    if search_query:
        query = query.join(
            Booking, Payment.booking_id == Booking.booking_id
        ).join(
            CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
        ).join(
            CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
        ).filter(
            (CustomerProfile.full_name.ilike(f'%{search_query}%')) |
            (CompanionProfile.display_name.ilike(f'%{search_query}%'))
        )
    
    # Apply sorting (newest first)
    query = query.order_by(Payment.payment_id.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    all_payments = pagination.items
    
    # Format payment data for template
    payments_data = []
    for payment in all_payments:
        booking = payment.booking
        customer = booking.customer if booking else None
        companion = booking.companion if booking else None
        
        # Calculate platform fee
        payment_platform_fee = float(payment.amount or 0) * (fee_percentage / 100)
        
        # Status mapping
        status_map = {
            PaymentStatusEnum.PENDING: 'PENDING',
            PaymentStatusEnum.PAID: 'COMPLETED',
            PaymentStatusEnum.REFUNDED: 'FAILED'
        }
        
        # Get primary photo for companion
        companion_avatar = None
        if companion and companion.photos:
            primary_photo = next((p for p in companion.photos if p.is_primary), companion.photos[0])
            companion_avatar = primary_photo.photo_url
            
        payments_data.append({
            'payment_id': payment.payment_id,
            'transaction_id': f'#TX-{payment.payment_id}',
            'booking_id': f'#BK-{booking.booking_id}' if booking else 'N/A',
            'customer_name': customer.full_name if customer else 'N/A',
            'customer_avatar': customer.profile_photo if customer else None,
            'companion_name': companion.display_name if companion else 'N/A',
            'companion_avatar': companion_avatar,
            'amount': float(payment.amount or 0),
            'platform_fee': payment_platform_fee,
            'status': status_map.get(payment.status, 'PENDING'),
            'created_at': payment.paid_at or datetime.now()
        })
    
    # Get pending count for sidebar badge
    from models import CompanionProfile as CP
    pending_count = CP.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/payments.html',
        active_page='payments',
        total_revenue=float(total_revenue),
        platform_fees=platform_fees,
        total_revenue_formatted="{:,.2f}".format(total_revenue),
        total_refunds=float(total_refunds),
        pending_refunds_count=refunded_count,
        failed_payments_count=failed_payments_count,
        payments=payments_data,
        pagination=pagination,
        pending_count=pending_count,
        search_query=search_query,
        status_filter=status_filter,
        fee_percentage=fee_percentage
    )

@app.get('/admin/payments/view/<int:id>')
@admin_required
@permission_required('payment:view')
def view_payment(id):
    from models.payments import Payment, PaymentStatusEnum
    from models.bookings import Booking
    
    # Get payment with booking details
    payment = Payment.query.filter_by(payment_id=id).first_or_404()
    booking = payment.booking
    customer = booking.customer if booking else None
    companion = booking.companion if booking else None
    
    # Calculate platform fee from settings
    fee_percentage = float(SystemSetting.get_value('platform_fee', 15))
    platform_fee = float(payment.amount or 0) * (fee_percentage / 100)
    companion_earning = float(payment.amount or 0) - platform_fee
    
    # Get pending count for sidebar
    from models import CompanionProfile as CP
    pending_count = CP.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/payment/view_detail.html',
        active_page='payments',
        payment=payment,
        booking=booking,
        customer=customer,
        companion=companion,
        platform_fee=platform_fee,
        companion_earning=companion_earning,
        pending_count=pending_count
    )

@app.post('/admin/payments/refund/<int:id>')
@admin_required
@permission_required('payment:refund')
def refund_payment(id):
    from flask import flash, redirect, url_for
    from models import Notification
    
    payment = Payment.query.filter_by(payment_id=id).first()
    if not payment:
        flash('Payment not found', 'error')
        return redirect(url_for('payments'))
    
    if payment.status == PaymentStatusEnum.REFUNDED:
        flash('This payment has already been refunded', 'warning')
        return redirect(url_for('payments'))
    
    # Update payment status to refunded
    payment.status = PaymentStatusEnum.REFUNDED
    
    # Update booking status to rejected
    booking = payment.booking
    if booking:
        from models.bookings import BookingStatusEnum
        booking.status = BookingStatusEnum.REJECTED
        
        # Create notification for customer
        if booking.customer:
            notification = Notification(
                user_id=booking.customer.user_id,
                title='Payment Refunded',
                message=f'Your payment of ${float(payment.amount):.2f} for booking #{booking.booking_id} has been refunded.',
                is_read=False
            )
            db.session.add(notification)
    
    db.session.commit()
    
    # Log action
    from flask import request
    AuditLog.log(
        user_id=session.get('user_id'),
        action='REFUND_PAYMENT',
        target_type='PAYMENT',
        target_id=id,
        details=f"Refunded payment #{id} of ${float(payment.amount):.2f} for booking #{booking.booking_id if booking else 'N/A'}",
        ip_address=request.remote_addr
    )
    
    flash(f'Payment #{payment.payment_id} has been refunded successfully!', 'success')
    return redirect(url_for('payments'))

@app.get('/admin/payments/export')
@admin_required
@permission_required('payment:view')
def export_payments():
    # Get query parameters for filtering
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    
    # Platform fee from settings
    fee_percentage = float(SystemSetting.get_value('platform_fee', 15))
    
    # Build query (reusing same logic as payments() view)
    query = Payment.query
    
    status_enum_map = {
        'COMPLETED': [PaymentStatusEnum.PAID],
        'PENDING': [PaymentStatusEnum.PENDING],
        'FAILED': [PaymentStatusEnum.REFUNDED],
    }
    
    if status_filter and status_filter in status_enum_map:
        query = query.filter(Payment.status.in_(status_enum_map[status_filter]))
    
    if search_query:
        query = query.join(
            Booking, Payment.booking_id == Booking.booking_id
        ).join(
            CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
        ).join(
            CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
        ).filter(
            (CustomerProfile.full_name.ilike(f'%{search_query}%')) |
            (CompanionProfile.display_name.ilike(f'%{search_query}%'))
        )
    
    all_payments = query.all()
    
    # Create CSV response
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'Transaction ID', 'Booking ID', 'Customer Name', 'Companion Name', 
        'Gross Amount ($)', 'Platform Fee ($)', 'Status', 'Date'
    ])
    
    # Data rows
    for payment in all_payments:
        booking = payment.booking
        customer = booking.customer if booking else None
        companion = booking.companion if booking else None
        
        payment_platform_fee = float(payment.amount or 0) * (fee_percentage / 100)
        
        status_map = {
            PaymentStatusEnum.PENDING: 'PENDING',
            PaymentStatusEnum.PAID: 'COMPLETED',
            PaymentStatusEnum.REFUNDED: 'FAILED'
        }
        
        writer.writerow([
            f'#TX-{payment.payment_id}',
            f'#BK-{booking.booking_id}' if booking else 'N/A',
            customer.full_name if customer else 'Unknown',
            companion.display_name if companion else 'Unknown',
            f"{float(payment.amount or 0):.2f}",
            f"{payment_platform_fee:.2f}",
            status_map.get(payment.status, 'PENDING'),
            (payment.paid_at or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Audit log
    AuditLog.log(
        user_id=session.get('user_id'),
        action='EXPORT_PAYMENTS',
        target_type='PAYMENT',
        target_id=0,
        details=f"Exported {len(all_payments)} payments to CSV (Filter: {status_filter}, Search: {search_query})",
        ip_address=request.remote_addr
    )
    
    output.seek(0)
    response = make_response(output.getvalue())
    filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/csv"
    return response