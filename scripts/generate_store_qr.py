import sys
import os

# Add parent directory to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from bakong_khqr import KHQR
from bakong_khqr.sdk.crc import CRC
import qrcode
import time

def generate():
    with app.app_context():
        token = app.config.get('KHQR_TOKEN', '')
        if not token:
            print("No KHQR_TOKEN found in config!")
            return
            
        khqr = KHQR(token)
        qr_string = khqr.create_qr(
            bank_account=app.config.get('KHQR_BANK_ACCOUNT'),
            merchant_name=app.config.get('KHQR_MERCHANT_NAME'),
            merchant_city=app.config.get('KHQR_MERCHANT_CITY'),
            amount=0,
            currency=app.config.get('KHQR_CURRENCY', 'KHR'),
            store_label=app.config.get('KHQR_STORE_LABEL'),
            phone_number=app.config.get('KHQR_PHONE_NUMBER'),
            bill_number='', 
            terminal_label=app.config.get('KHQR_TERMINAL_LABEL'),
            static=True
        )
        
        # When creating a TRULY static QR that is printed and put on a wall,
        # it should NOT have a timestamp tag (tag 99). Otherwise it naturally expires!
        # bakong_khqr adds this tag even on static QRs, causing expiration issues.
        
        # The QR string structure at the end: ...[Tag 99 (21 characters)][Tag 63 CRC (8 characters)]
        body = qr_string[:-8] # Remove CRC
        if "99170013" in body[-21:]:
            # Strip the 21 character timestamp tag
            body_without_timestamp = body[:-21]
            # Recalculate CRC
            crc_generator = CRC()
            # The .value() method of CRC takes string, appends "6304" and calculates hash
            new_crc = crc_generator.value(body_without_timestamp)
            final_qr_string = body_without_timestamp + new_crc
            print("Successfully stripped expiring timestamp for a permanent static QR!")
        else:
            final_qr_string = qr_string
            
        # Generate the visual QR Code image
        qr_obj = qrcode.QRCode(box_size=10, border=4)
        qr_obj.add_data(final_qr_string)
        qr_obj.make(fit=True)
        img = qr_obj.make_image(fill_color='black', back_color='white')
        
        output_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'qrcode.png')
        img.save(output_path)
        print(f"Generated new permanent QR code at: {output_path}")

if __name__ == '__main__':
    generate()
