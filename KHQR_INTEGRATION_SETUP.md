# KHQR Integration Setup Guide

## Overview

The KHQR (Bakong) QR code payment service has been successfully integrated as a **standalone payment module** within RentACompanion. It operates independently alongside the Stripe card payment system.

## What Was Added

### 1. Service Layer
- **`services/khqr_service.py`** - Core KHQR service class
  - `generate_checkout()` - Generate QR codes
  - `check_payment()` - Query Bakong API
  - `is_payment_successful()` - Verify payment status

### 2. Route Handlers
- **`route/khqr_routes.py`** - KHQR API endpoints
  - `POST /khqr/checkout` - Initialize payment
  - `POST /khqr/check-payment` - Check payment status
  - `GET /khqr/payment/<booking_id>` - Display payment page

### 3. Templates
- **`templates/khqr/payment.html`** - QR code payment UI
- **`templates/khqr/success.html`** - Success page

### 4. Database
- Added `KHQR` to `PaymentMethodEnum`
- Migration: `khqr_integration_001_add_khqr_payment.py`

### 5. Configuration
- Added KHQR settings to `app.py`

## Installation

### 1. Install Dependencies

```bash
pip install bakong_khqr qrcode requests Pillow urllib3
```

Or add to requirements.txt:
```
bakong_khqr
qrcode
requests
Pillow
urllib3
```

### 2. Apply Database Migration

```bash
cd rentalGirlfriend
flask db upgrade
```

### 3. Verify Configuration

Check `app.py` for KHQR settings:
```python
app.config["KHQR_ENABLED"] = True
app.config["KHQR_TOKEN"] = "your_token"
app.config["KHQR_BANK_ACCOUNT"] = "your_account@bkrt"
# ... other settings
```

## Usage

### Option A: Standalone KHQR Payment Page

Access directly:
```
GET /khqr/payment/{booking_id}
```

Example:
```
http://localhost:5000/khqr/payment/123
```

### Option B: API Integration

1. **Initiate Payment**
```bash
curl -X POST http://localhost:5000/khqr/checkout \
  -H "Content-Type: application/json" \
  -d '{"booking_id": 123}'
```

Response:
```json
{
  "md5": "abc123def456",
  "qr_base64": "data:image/png;base64,iVBORw0K...",
  "amount": 100000,
  "currency": "KHR"
}
```

2. **Display QR Code**
```html
<img src="{{ qr_base64 }}" alt="QR Code">
```

3. **Check Payment Status**
```bash
curl -X POST http://localhost:5000/khqr/check-payment \
  -H "Content-Type: application/json" \
  -d '{"md5": "abc123def456"}'
```

## Architecture Diagram

```
Customer Booking
       ↓
Payment Method Selection
       ├─→ Stripe Card
       └─→ KHQR QR Code
            ├─→ /khqr/checkout (POST)
            │    ├─ Generate QR code
            │    └─ Store LN session
            ├─→ Display payment.html
            │    └─ Show QR code
            ├─→ Customer Scans & Pays
            └─→ /khqr/check-payment (POST)
                 ├─ Query Bakong API
                 ├─ Create Payment record
                 └─ Redirect to receipt
```

## File Structure

```
rentalGirlfriend/
├── app.py                           # Add KHQR config
├── models/
│   └── payments.py                  # Add KHQR enum
├── services/
│   ├── __init__.py                  # Empty module init
│   └── khqr_service.py              # KHQR service class
├── route/
│   └── khqr_routes.py               # KHQR route handlers
├── templates/
│   └── khqr/
│       ├── payment.html             # QR payment page
│       └── success.html             # Success page
├── migrations/
│   └── versions/
│       └── khqr_integration_001_*.py # Migration file
└── KHQR_SERVICE_README.md           # Detailed documentation
```

## Configuration Reference

| Setting | Purpose | Default |
|---------|---------|---------|
| `KHQR_ENABLED` | Enable/disable service | True |
| `KHQR_TOKEN` | Bakong API token | - |
| `KHQR_BANK_ACCOUNT` | Bank account ID | - |
| `KHQR_MERCHANT_NAME` | Business name | RentACompanion |
| `KHQR_MERCHANT_CITY` | Business city | Phnom Penh |
| `KHQR_PHONE_NUMBER` | Contact number | 855884777905 |
| `KHQR_STORE_LABEL` | Store name | MShop |
| `KHQR_TERMINAL_LABEL` | Terminal ID | Cashier-01 |
| `KHQR_CURRENCY` | Currency code | KHR |
| `KHQR_EXCHANGE_RATE` | USD to KHR rate | 4100 |

## Security Checklist

- [ ] KHQR_TOKEN is stored securely (use environment variables in production)
- [ ] SSL certificate verification enabled (set `verify=True` in khqr_routes.py)
- [ ] Database migration applied
- [ ] User authorization checks verified on all endpoints
- [ ] Session validation in place

## Testing

### Test QR Generation

```python
from services.khqr_service import KHQRPaymentService

service = KHQRPaymentService("your_token")
result = service.generate_checkout(
    amount=100000,
    currency='KHR',
    merchant_name='Test'
)

print(f"MD5: {result['md5']}")
print(f"QR Length: {len(result['qr_base64'])}")
```

### Test Payment Check

```python
response = service.check_payment(result['md5'])
print(f"Status: {response.get('responseCode')}")

# Check if payment successful
is_paid = service.is_payment_successful(response)
print(f"Paid: {is_paid}")
```

## Troubleshooting

### 1. "KHQR service not configured"
- Verify `KHQR_TOKEN` is set in `app.py`
- Check Flask app is initialized with KHQR config

### 2. "QR code appears broken"
- Ensure `bakong_khqr` is installed correctly
- Check token validity
- Verify account details are correct

### 3. "Payment not detected"
- Check Bakong transaction completed
- Verify MD5 matches
- API may need 3-5 seconds to process
- Check network connectivity

### 4. "Import Error: route.khqr_routes"
- Ensure `khqr_routes.py` exists in `route/` folder
- Run Flask app from root directory
- Check `__init__.py` files exist

## Next Steps

1. ✅ Integration complete
2. ⬜ Configure production Bakong credentials
3. ⬜ Enable SSL certificate verification
4. ⬜ Set up error logging
5. ⬜ Test with real bookings
6. ⬜ Add KHQR option to main payment selection UI

## Support

For detailed technical documentation, see `KHQR_SERVICE_README.md`

For Bakong API documentation, visit: https://bakong.nbc.gov.kh/
