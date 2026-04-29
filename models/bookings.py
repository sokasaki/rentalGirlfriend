from extensions import db
from enum import Enum

class BookingStatusEnum(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"
    COMPLETED = "COMPLETED"

class Booking(db.Model):
    __tablename__ = 'bookings'
    booking_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_profiles.customer_id'), nullable=False)
    companion_id = db.Column(db.Integer, db.ForeignKey('companion_profiles.companion_id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(BookingStatusEnum), default=BookingStatusEnum.PENDING)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    meeting_location = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Relationships
    payments = db.relationship('Payment', backref='booking', lazy=True)
    review = db.relationship('Review', backref='booking', lazy=True, uselist=False)