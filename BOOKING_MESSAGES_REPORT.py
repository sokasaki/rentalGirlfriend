from app import app, db
from models import Booking, BookingStatusEnum, User, CompanionProfile, CustomerProfile

print('='*90)
print('BOOKING MESSAGES REPORT')
print('='*90)

print('\n' + '='*90)
print('1. CUSTOMER BOOKING CREATION FLOW')
print('='*90)

print('\n▶ When customer clicks "Proceed to Book":')
print('  └─> Goes to: /create_booking (POST)')
print('\nValidation & Messages:')

messages = {
    'login_required': {
        'condition': 'User not logged in',
        'message': 'Please login to make a booking',
        'status': 401
    },
    'profile_not_found': {
        'condition': 'Customer profile not found',
        'message': 'Customer profile not found. Please complete your registration.',
        'status': 404
    },
    'companion_not_found': {
        'condition': 'Companion ID invalid',
        'message': 'Companion not found',
        'status': 404
    },
    'companion_not_approved': {
        'condition': 'Companion verification_status != APPROVED',
        'message': 'This companion is not currently available for booking',
        'status': 400
    },
    'different_dates': {
        'condition': 'Booking starts and ends on different days',
        'message': 'Booking must start and end on the same day',
        'status': 400
    },
    'past_date': {
        'condition': 'Booking time is in the past',
        'message': 'Booking time must be in the future',
        'status': 400
    },
    'not_available': {
        'condition': 'Date/time outside companion availability',
        'message': 'Selected date/time is outside companion availability',
        'status': 400
    },
    'overlapping': {
        'condition': 'Companion already has booking at that time',
        'message': 'This time slot is no longer available. Please choose another time.',
        'status': 409
    },
    'success': {
        'condition': 'All validations pass',
        'message': 'Booking request sent successfully! Waiting for companion approval. Total: ${amount}',
        'status': 201
    }
}

for i, (key, msg) in enumerate(messages.items(), 1):
    print(f'\n  {i}. {msg["condition"]}')
    print(f'     Message: "{msg["message"]}"')
    print(f'     Status: {msg["status"]}')

print('\n' + '='*90)
print('2. COMPANION BOOKING APPROVAL FLOW')
print('='*90)

print('\n▶ When companion clicks "Approve" on PENDING booking:')
print('  └─> Goes to: /approve_booking/<booking_id> (POST)')
print('\nValidation & Messages:')

approval_messages = {
    'not_logged_in': {
        'condition': 'User not logged in',
        'message': 'Please login first',
        'status': 401
    },
    'booking_not_found': {
        'condition': 'Booking ID doesn\'t exist',
        'message': 'Booking not found',
        'status': 404
    },
    'unauthorized': {
        'condition': 'User is not the companion for this booking',
        'message': 'Unauthorized to approve this booking',
        'status': 403
    },
    'wrong_status': {
        'condition': 'Booking status is not PENDING',
        'message': 'Booking cannot be approved. Current status: {status}',
        'status': 400
    },
    'success': {
        'condition': 'Companion approves booking',
        'message': 'Booking approved successfully! Customer can now proceed with payment.',
        'status': 200
    }
}

for i, (key, msg) in enumerate(approval_messages.items(), 1):
    print(f'\n  {i}. {msg["condition"]}')
    print(f'     Message: "{msg["message"]}"')

print('\n' + '='*90)
print('3. COMPANION BOOKING REJECTION FLOW')
print('='*90)

print('\n▶ When companion clicks "Reject" on PENDING booking:')
print('  └─> Goes to: /reject_booking/<booking_id> (POST)')
print('\nValidation & Messages:')

rejection_messages = {
    'not_logged_in': {
        'condition': 'User not logged in',
        'message': 'Please login first',
        'status': 401
    },
    'booking_not_found': {
        'condition': 'Booking ID doesn\'t exist',
        'message': 'Booking not found',
        'status': 404
    },
    'unauthorized': {
        'condition': 'User is not the companion for this booking',
        'message': 'Unauthorized to reject this booking',
        'status': 403
    },
    'wrong_status': {
        'condition': 'Booking status is not PENDING',
        'message': 'Booking cannot be rejected. Current status: {status}',
        'status': 400
    },
    'success': {
        'condition': 'Companion rejects booking',
        'message': 'Booking rejected successfully.',
        'status': 200
    }
}

for i, (key, msg) in enumerate(rejection_messages.items(), 1):
    print(f'\n  {i}. {msg["condition"]}')
    print(f'     Message: "{msg["message"]}"')

print('\n' + '='*90)
print('4. NOTIFICATION MESSAGES (Seed Data)')
print('='*90)

notifications = [
    'Welcome to RentACompanion! Complete your profile to get started.',
    'You have a new booking request. Check your dashboard.',
    'Your booking has been confirmed. Have a great time!',
    'Payment received successfully. Thank you!',
    'You received a new 5-star review! Keep up the great work.',
]

for i, notif in enumerate(notifications, 1):
    print(f'\n  {i}. {notif}')

print('\n' + '='*90)
print('5. COMPANION APPROVAL/REJECTION NOTIFICATIONS')
print('='*90)

print('\n▶ When Admin approves companion:')
print('  Title: "Application Approved"')
print('  Message: "Congratulations! Your companion application has been approved. ')
print('           You can now start receiving bookings."')

print('\n▶ When Admin rejects companion:')
print('  Title: "Application Rejected"')
print('  Message: "Unfortunately, your companion application has been rejected. ')
print('           Reason: {admin_provided_reason}"')

print('\n' + '='*90)
print('6. BOOKING STATUS FLOW')
print('='*90)

statuses = {
    'PENDING': {
        'who': 'Customer',
        'description': 'Booking request sent, waiting for companion approval',
        'next_status': 'APPROVED or REJECTED'
    },
    'APPROVED': {
        'who': 'Companion',
        'description': 'Companion approved, customer can proceed with payment',
        'next_status': 'PAID'
    },
    'REJECTED': {
        'who': 'Companion',
        'description': 'Companion rejected the booking',
        'next_status': 'None (End state)'
    },
    'PAID': {
        'who': 'Customer',
        'description': 'Payment received and processed',
        'next_status': 'COMPLETED'
    },
    'COMPLETED': {
        'who': 'System',
        'description': 'Booking completed and fulfilled',
        'next_status': 'None (End state)'
    }
}

for status, info in statuses.items():
    print(f'\n  {status}')
    print(f'    Set by: {info["who"]}')
    print(f'    Meaning: {info["description"]}')
    print(f'    Next: {info["next_status"]}')

print('\n' + '='*90)
print('7. KEY SUMMARY')
print('='*90)

print('''
BOOKING LIFECYCLE:

1. Customer Creates Booking
   ↓ (Validation checks: date available? time valid? companion approved?)
   ↓
   SUCCESS: "Booking request sent successfully! Waiting for companion approval. Total: $XXX"
   
   OR
   
   FAILURE: Shows specific error message (not available, past date, etc.)

2. Companion Reviews Booking (Dashboard shows pending requests)
   ↓ (Can APPROVE or REJECT)
   
   If APPROVE:
   ├─ Message: "Booking approved successfully! Customer can now proceed with payment."
   └─ Status: PENDING → APPROVED
   
   If REJECT:
   ├─ Message: "Booking rejected successfully."
   └─ Status: PENDING → REJECTED

3. Customer Sees APPROVED Booking (in dashboard)
   ↓
   Sees "Proceed to Payment" button
   ↓
   Chooses payment method (Stripe or KHQR)

4. Payment Processing
   ├─ Stripe: Uses Card payment
   └─ KHQR: Uses Bakong QR code
   
5. Payment Success
   ├─ Message: Redirect to receipt page
   └─ Status: APPROVED → PAID

6. Booking Completed
   └─ Status: PAID → COMPLETED (when date/time passes)

NOTIFICATION TIMING:
├─ Companion approval/rejection: Immediately
├─ New booking to companion: Via dashboard notification
├─ Payment received: To customer after payment success
└─ Admin approval: To new companion applicants
''')

print('='*90)
