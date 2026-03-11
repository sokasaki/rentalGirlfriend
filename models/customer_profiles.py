from extensions import db
from enum import Enum

class GenderEnum(Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

class CustomerProfile(db.Model):
    __tablename__ = 'customer_profiles'
    customer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.Enum(GenderEnum), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)
    cover_photo = db.Column(db.String(255), nullable=True)

    # Relationships
    bookings = db.relationship('Booking', backref='customer', lazy=True)
    favorites = db.relationship('Favorite', backref='customer', lazy=True)