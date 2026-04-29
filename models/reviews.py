from extensions import db
from datetime import datetime
from enum import Enum

class ReviewStatusEnum(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Review(db.Model):
    __tablename__ = 'reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.booking_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    reply = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Moderation fields
    status = db.Column(db.Enum(ReviewStatusEnum), default=ReviewStatusEnum.APPROVED)
    moderated_at = db.Column(db.DateTime, nullable=True)
    moderated_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)