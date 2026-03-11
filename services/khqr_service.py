"""
KHQR (Bakong) Payment Service
Standalone QR code payment service for the RentACompanion application
"""

import time
import qrcode
import requests
import io
import base64
from bakong_khqr import KHQR


class KHQRPaymentService:
    """Service for managing KHQR/Bakong QR code payments"""
    
    def __init__(self, token):
        """
        Initialize KHQR service with authentication token
        
        Args:
            token (str): Bakong KHQR API token
        """
        self.token = token
        self.khqr = KHQR(token)
    
    def generate_checkout(self, amount, currency='KHR', merchant_name='RentACompanion', 
                         merchant_city='Phnom Penh', phone_number='855884777905',
                         bank_account='nol_piseth@bkrt', store_label='MShop',
                         terminal_label='Cashier-01', bill_number=None):
        """
        Generate KHQR checkout data with QR code
        
        Args:
            amount (int/float): Payment amount
            currency (str): Currency code (default: KHR)
            merchant_name (str): Merchant name
            merchant_city (str): Merchant city
            phone_number (str): Phone number
            bank_account (str): Bank account ID
            store_label (str): Store label
            terminal_label (str): Terminal label
            bill_number (str): Unique bill number (auto-generated if None)
        
        Returns:
            dict: Contains md5, qr_base64, amount, and currency
        """
        if bill_number is None:
            bill_number = f"TRX{int(time.time())}"
        
        # Create KHQR QR string
        qr_string = self.khqr.create_qr(
            bank_account=bank_account,
            merchant_name=merchant_name,
            merchant_city=merchant_city,
            amount=amount,
            currency=currency,
            store_label=store_label,
            phone_number=phone_number,
            bill_number=bill_number,
            terminal_label=terminal_label,
            static=False
        )
        
        # Generate MD5 for transaction tracking
        md5 = self.khqr.generate_md5(qr_string)
        
        # Generate QR code image
        qr_obj = qrcode.QRCode(
            box_size=10, 
            border=4, 
            version=1, 
            error_correction=qrcode.constants.ERROR_CORRECT_L
        )
        qr_obj.add_data(qr_string)
        qr_obj.make(fit=True)
        img = qr_obj.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        
        return {
            'md5': md5,
            'qr_base64': qr_base64,
            'amount': amount,
            'currency': currency,
            'bill_number': bill_number,
            'qr_string': qr_string
        }
    
    def check_payment(self, md5):
        """
        Check if payment was completed
        
        Args:
            md5 (str): Transaction MD5 hash
        
        Returns:
            dict: API response from Bakong
        """
        response = requests.post(
            'https://api-bakong.nbc.gov.kh/v1/check_transaction_by_md5',
            json={'md5': md5},
            headers={
                'authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            },
            verify=False
        )
        
        return response.json()
    
    def is_payment_successful(self, response):
        """
        Check if payment response indicates successful payment
        
        Args:
            response (dict): API response from check_payment
        
        Returns:
            bool: True if payment is successful
        """
        response_code = response.get('responseCode')
        return str(response_code) in {'0', '00'}
