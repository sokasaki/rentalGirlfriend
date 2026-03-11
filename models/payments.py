from extensions import db
from enum import Enum
from datetime import datetime

class PaymentMethodEnum(Enum):
    ABA = "ABA"
    CARD = "CARD"
    KHQR = "KHQR"
    WING = "WING"

class PaymentStatusEnum(Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    REFUNDED = "REFUNDED"

class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.booking_id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.Enum(PaymentMethodEnum), nullable=False)
    status = db.Column(db.Enum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    paid_at = db.Column(db.DateTime, nullable=True)