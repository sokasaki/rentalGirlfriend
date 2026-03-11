# KHQR (Bakong) QR Code Payment Service

A standalone QR code payment service integrated into RentACompanion using Bakong's KHQR platform.

## Overview

The KHQR service operates as a **separate, optional payment module** alongside the main Stripe card payment system. It allows customers to pay for bookings using QR codes compatible with Bakong banking system.

## Features

- **Dynamic QR Code Generation**: Creates unique QR codes for each transaction
- **Real-time Payment Verification**: Polls Bakong API to verify payment status
- **Session-based Tracking**: Maintains booking-to-payment relationships
- **Separate Route Namespace**: All KHQR endpoints use `/khqr/` prefix
- **Independent Templates**: KHQR payment UI is separate from main payment flow

## Architecture

```
services/
├── khqr_service.py          # Core KHQR service class
│
route/
├── khqr_routes.py           # KHQR payment route handlers
│
templates/
├── khqr/
│   ├── payment.html         # QR code payment page
│   └── success.html         # Payment success page
```

## Usage

### 1. Initialize KHQR Payment

**Endpoint**: `POST /khqr/checkout`

Request:

```json
{
  "booking_id": 123
}
```

Response:

```json
{
  "md5": "transaction_hash",
  "qr_base64": "data:image/png;base64,iVBORw0K...",
  "amount": 100000,
  "currency": "KHR"
}
```

### 2. Check Payment Status

**Endpoint**: `POST /khqr/check-payment`

Request:

```json
{
  "md5": "transaction_hash"
}
```

Response (on success):

```json
{
  "responseCode": 0,
  "redirect": "/receipt/456"
}
```

## Configuration

Add to `app.py`:

```python
# KHQR Configuration
app.config["KHQR_ENABLED"] = True
app.config["KHQR_TOKEN"] = "your_token_here"
app.config["KHQR_BANK_ACCOUNT"] = "account@bank"
app.config["KHQR_MERCHANT_NAME"] = "Your Business"
app.config["KHQR_MERCHANT_CITY"] = "City"
app.config["KHQR_PHONE_NUMBER"] = "+855xxxxxxxxx"
app.config["KHQR_STORE_LABEL"] = "Store Name"
app.config["KHQR_TERMINAL_LABEL"] = "Cashier-01"
app.config["KHQR_CURRENCY"] = "KHR"
app.config["KHQR_EXCHANGE_RATE"] = 4100  # USD to KHR
```

## Dependencies

```
bakong_khqr
qrcode
requests
Pillow
urllib3
```

Install with:

```bash
pip install bakong_khqr qrcode requests Pillow urllib3
```

## Database Changes

Add KHQR to `PaymentMethodEnum` in `models/payments.py`:

```python
class PaymentMethodEnum(Enum):
    ABA = "ABA"
    CARD = "CARD"
    KHQR = "KHQR"  # New
    WING = "WING"
```

Create migration:

```bash
flask db migrate -m "Add KHQR payment method"
flask db upgrade
```

## How It Works

1. **Customer initiates KHQR payment**
   - POST `/khqr/checkout` with booking_id
   - Service generates dynamic QR code
   - QR data stored in session

2. **Payment UI displays QR code**
   - Customer scans with Bakong app
   - Payment is made

3. **Payment verification**
   - Frontend polls `/khqr/check-payment` every 3 seconds
   - Service queries Bakong API via MD5 hash
   - On success: booking marked PAID, payment record created

4. **Completion**
   - Customer redirected to receipt page
   - Booking status updated to PAID

## Security Notes

- ✅ Session-based validation ensures booking owner matches
- ✅ Payment records validated against DB before creation
- ✅ MD5 tracking prevents duplicate payments
- ⚠️ SSL certificate verification disabled for development (line: `verify=False`)
  - Should be enabled in production
- ✅ Authorization checks on all endpoints

## Troubleshooting

### QR Code Not Displaying

- Verify bakong_khqr library is installed
- Check KHQR_TOKEN is valid
- Ensure static file serving is configured

### Bakong API Errors

- Verify KHQR_BANK_ACCOUNT format
- Check internet connectivity
- Ensure API token hasn't expired

### Payment Not Detected

- Verify MD5 is correctly generated
- Check Bakong transaction is complete
- API may have processing delay (retry after 3 seconds)

## Testing

Test KHQR payment flow:

```python
from services.khqr_service import KHQRPaymentService

service = KHQRPaymentService("your_token")

# Generate QR
checkout = service.generate_checkout(100000, currency='KHR')
print(f"MD5: {checkout['md5']}")
print(f"QR: {checkout['qr_base64'][:50]}...")

# Check payment
response = service.check_payment(checkout['md5'])
print(f"Response: {response}")
```

## Future Enhancements

- [ ] Webhook support for instant payment notifications
- [ ] Payment timeout handling
- [ ] Batch QR generation
- [ ] Payment history dashboard
- [ ] Integration with accounting system
