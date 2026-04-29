"""
Clean KHQR (Bakong) payment service.

This service keeps the existing app flow, but removes the old sandbox-style
timestamp shifting and centralizes KHQR payload validation/normalization.
"""

import base64
import re
from decimal import Decimal, InvalidOperation

import requests
from bakong_khqr import KHQR


class KHQRPaymentService:
    """Generate KHQR payloads and check payment status."""

    # Correct Sandbox (SIT) URL
    CHECK_PAYMENT_URL = "https://sit-api-bakong.nbc.gov.kh/v1/check_transaction_by_md5"

    def __init__(self, token):
        token = (token or "").strip().strip('"\'')
        if not token:
            raise ValueError("KHQR token is required.")

        self.token = token
        self.khqr = KHQR(token)

    @staticmethod
    def _normalize_phone_number(phone_number):
        digits = "".join(ch for ch in str(phone_number or "") if ch.isdigit())
        if not digits:
            raise ValueError("KHQR phone number is required.")

        if digits.startswith("855"):
            digits = digits[3:]
        if not digits.startswith("0"):
            digits = "0" + digits

        if not re.fullmatch(r"0\d{8,9}", digits):
            raise ValueError(
                "KHQR phone number must normalize to a Cambodian mobile number like 088777905 or 0884777905."
            )

        return digits

    @staticmethod
    def _normalize_bank_account(bank_account):
        account = str(bank_account or "").strip()
        if not account:
            raise ValueError("KHQR bank account is required.")
        if "@" not in account:
            raise ValueError("KHQR bank account must look like username@bank.")
        return account

    @staticmethod
    def _clean_text(value, field_name, max_length):
        cleaned = " ".join(str(value or "").split()).strip()
        if not cleaned:
            raise ValueError(f"{field_name} is required.")
        if len(cleaned) > max_length:
            raise ValueError(f"{field_name} cannot exceed {max_length} characters.")
        return cleaned

    @staticmethod
    def _normalize_amount(amount, currency, static):
        if static:
            return 0

        try:
            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("KHQR amount must be numeric.") from exc

        if decimal_amount <= 0:
            raise ValueError("KHQR amount must be greater than zero.")

        if currency == "KHR":
            decimal_amount = decimal_amount.quantize(Decimal("1"))
            return int(decimal_amount)

        decimal_amount = decimal_amount.quantize(Decimal("0.01"))
        return float(decimal_amount)

    def generate_checkout(
        self,
        amount,
        currency="KHR",
        merchant_name="RentACompanion",
        merchant_city="Phnom Penh",
        phone_number="855884777905",
        bank_account="nol_piseth@bkrt",
        store_label="MShop",
        terminal_label="Cashier-01",
        bill_number=None,
        static=False,
    ):
        """Generate KHQR payload plus base64 QR image."""
        currency = self._clean_text(currency, "Currency", 3).upper()
        if currency not in {"KHR", "USD"}:
            raise ValueError("KHQR currency must be KHR or USD.")

        normalized_bank_account = self._normalize_bank_account(bank_account)
        normalized_phone = self._normalize_phone_number(phone_number)
        merchant_name = self._clean_text(merchant_name, "Merchant name", 25)
        merchant_city = self._clean_text(merchant_city, "Merchant city", 15)
        store_label = self._clean_text(store_label, "Store label", 25)
        terminal_label = self._clean_text(terminal_label, "Terminal label", 25)
        bill_number = self._clean_text(bill_number or "STATIC", "Bill number", 25)
        normalized_amount = self._normalize_amount(amount, currency, static)

        qr_string = self.khqr.create_qr(
            bank_account=normalized_bank_account,
            merchant_name=merchant_name,
            merchant_city=merchant_city,
            amount=normalized_amount,
            currency=currency,
            store_label=store_label,
            phone_number=normalized_phone,
            bill_number=bill_number,
            terminal_label=terminal_label,
            static=static,
        )
        md5 = self.khqr.generate_md5(qr_string)
        
        # Generate raw QR code using qrcode library for a clean look
        import qrcode
        import io
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=1,
        )
        qr.add_data(qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()

        return {
            "md5": md5,
            "qr_base64": qr_base64,
            "amount": normalized_amount if not static else amount,
            "currency": currency,
            "bill_number": bill_number,
            "qr_string": qr_string,
            "phone_number": normalized_phone,
            "bank_account": normalized_bank_account,
        }

    def check_payment(self, md5):
        """Check payment state using Bakong transaction API."""
        response = requests.post(
            self.CHECK_PAYMENT_URL,
            json={"md5": md5},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code == 401:
            raise ValueError(
                "Bakong rejected KHQR_TOKEN with 401 Unauthorized. "
                "The token may be invalid, inactive, or for a different Bakong environment."
            )
        if response.status_code == 403:
            raise ValueError(
                "Bakong rejected the request with 403 Forbidden. "
                "The API may only allow approved IP addresses or Cambodia-based access."
            )
        if response.status_code >= 400:
            raise ValueError(
                f"Bakong payment check failed with HTTP {response.status_code}: {response.text}"
            )

        return response.json()

    @staticmethod
    def is_payment_successful(response):
        """Return True when Bakong reports a successful payment."""
        return str(response.get("responseCode")) in {"0", "00"}
