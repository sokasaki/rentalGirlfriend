"""
KHQR Payment Routes
Separate routes for KHQR/Bakong QR code payment handling
"""

from app import app, render_template, db
from flask import request, jsonify, url_for, session, redirect
from models.bookings import Booking, BookingStatusEnum
from models.customer_profiles import CustomerProfile
from models.payments import Payment, PaymentStatusEnum
from services.khqr_service import KHQRPaymentService
from datetime import datetime
from decimal import Decimal

def _get_khqr_service():
    """Create KHQR service from current app config when enabled and configured."""
    if not app.config.get('KHQR_ENABLED', True):
        return None

    token = (app.config.get('KHQR_TOKEN') or '').strip().strip('"\'')
    if not token:
        return None

    return KHQRPaymentService(token)


def _calculate_total_with_fee(booking):
    """Calculate total with 10% service fee"""
    subtotal = float(booking.total_price)
    service_fee = subtotal * 0.1
    return subtotal + service_fee


@app.post('/khqr/checkout')
def khqr_checkout():
    """
    Initialize KHQR payment checkout for a booking
    Returns QR code and payment details
    """
    khqr_service = _get_khqr_service()
    if not khqr_service:
        return jsonify({'error': 'KHQR service not configured'}), 503
    
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        booking_id = data.get('booking_id')
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
        if not customer or booking.customer_id != customer.customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if booking.status != BookingStatusEnum.APPROVED:
            return jsonify({'error': 'Booking must be approved before payment'}), 400
        
        # DEMO: Set fixed amount of 100 KHR for testing
        amount = 100
        currency = 'KHR'
        
        # Generate KHQR checkout
        bill_number = f"BK{booking.booking_id}"
        checkout_data = khqr_service.generate_checkout(
            amount=amount,
            currency=currency,
            merchant_name=app.config.get('KHQR_MERCHANT_NAME', 'RentACompanion'),
            merchant_city=app.config.get('KHQR_MERCHANT_CITY', 'Phnom Penh'),
            phone_number=app.config.get('KHQR_PHONE_NUMBER', '855884777905'),
            bank_account=app.config.get('KHQR_BANK_ACCOUNT'),
            store_label=app.config.get('KHQR_STORE_LABEL', 'MShop'),
            terminal_label=app.config.get('KHQR_TERMINAL_LABEL', 'Cashier-01'),
            bill_number=bill_number
        )
        
        # Store in session for verification
        session['khqr_md5'] = checkout_data['md5']
        session['khqr_booking_id'] = booking.booking_id
        session['khqr_amount'] = str(amount)
        session['khqr_currency'] = currency
        
        print(f"KHQR Checkout - DEMO MODE: Booking {booking_id}, Fixed Amount 100 KHR")
        
        print(f"KHQR Checkout: Booking {booking_id}, Bill {bill_number}, Amount {amount} {currency}")
        
        return jsonify({
            'md5': checkout_data['md5'],
            'qr_base64': checkout_data['qr_base64'],
            'amount': checkout_data['amount'],
            'currency': checkout_data['currency']
        })
    
    except Exception as e:
        print(f"KHQR checkout error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.post('/khqr/check-payment')
def khqr_check_payment():
    """
    Check if KHQR payment was completed
    """
    khqr_service = _get_khqr_service()
    if not khqr_service:
        return jsonify({'error': 'KHQR service not configured'}), 503
    
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json() or {}
        md5 = data.get('md5')
        
        if not md5:
            return jsonify({'error': 'Missing md5'}), 400
        
        booking_id = session.get('khqr_booking_id')
        if not booking_id:
            return jsonify({'error': 'No pending KHQR payment'}), 400
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
        if not customer or booking.customer_id != customer.customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check payment status
        response = khqr_service.check_payment(md5)
        paid = khqr_service.is_payment_successful(response)
        
        if not paid:
            # Return raw response for frontend
            return jsonify(response)
        
        # Payment confirmed - update booking and create payment record
        existing_payment = Payment.query.filter_by(
            booking_id=booking.booking_id,
            status=PaymentStatusEnum.PAID
        ).order_by(Payment.payment_id.desc()).first()
        
        if existing_payment:
            return jsonify({
                **response,
                'redirect': url_for('receipt', payment_id=existing_payment.payment_id)
            })
        
        # Create new payment record
        booking.status = BookingStatusEnum.PAID
        total = _calculate_total_with_fee(booking)
        
        payment = Payment(
            booking_id=booking.booking_id,
            amount=Decimal(str(total)),
            method='KHQR',  # Store as KHQR payment method
            status=PaymentStatusEnum.PAID,
            paid_at=datetime.now()
        )
        
        db.session.add(payment)
        db.session.commit()
        
        print(f"KHQR Payment confirmed: Booking {booking_id}, Payment {payment.payment_id}")
        
        return jsonify({
            **response,
            'redirect': url_for('receipt', payment_id=payment.payment_id)
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"KHQR check payment error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.get('/khqr/payment/<int:booking_id>')
def khqr_payment_page(booking_id):
    """
    Display KHQR payment QR code page for a booking
    """
    khqr_service = _get_khqr_service()
    if not khqr_service:
        return "KHQR service not configured", 503
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return "Booking not found", 404
        
        customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
        if not customer or booking.customer_id != customer.customer_id:
            return "Unauthorized", 403
        
        if booking.status != BookingStatusEnum.APPROVED:
            return f"Booking must be approved before payment", 400
        
        # DEMO: Set fixed amount of 100 KHR for testing
        amount = 100
        currency = 'KHR'
        
        bill_number = f"BK{booking.booking_id}"
        checkout_data = khqr_service.generate_checkout(
            amount=amount,
            currency=currency,
            merchant_name=app.config.get('KHQR_MERCHANT_NAME', 'RentACompanion'),
            merchant_city=app.config.get('KHQR_MERCHANT_CITY', 'Phnom Penh'),
            phone_number=app.config.get('KHQR_PHONE_NUMBER', '855884777905'),
            bank_account=app.config.get('KHQR_BANK_ACCOUNT'),
            store_label=app.config.get('KHQR_STORE_LABEL', 'MShop'),
            terminal_label=app.config.get('KHQR_TERMINAL_LABEL', 'Cashier-01'),
            bill_number=bill_number
        )
        
        # Store in session
        session['khqr_md5'] = checkout_data['md5']
        session['khqr_booking_id'] = booking.booking_id
        session['khqr_amount'] = str(amount)
        session['khqr_currency'] = currency
        
        print(f"KHQR Payment Page - DEMO MODE: Booking {booking_id}, Fixed Amount 100 KHR")
        
        return render_template(
            'khqr/payment.html',
            md5=checkout_data['md5'],
            qr_base64=checkout_data['qr_base64'],
            amount=checkout_data['amount'],
            currency=checkout_data['currency'],
            merchant_name=app.config.get('KHQR_MERCHANT_NAME', 'RentACompanion'),
            booking=booking
        )
    
    except Exception as e:
        print(f"KHQR payment page error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500
