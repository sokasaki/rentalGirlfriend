from extensions import db
from enum import Enum

class CompanionGenderEnum(Enum):
    FEMALE = "FEMALE"
    MALE = "MALE"
    NON_BINARY = "NON_BINARY"
    OTHER = "OTHER"

class VerificationStatusEnum(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class CompanionProfile(db.Model):
    __tablename__ = 'companion_profiles'
    companion_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.Enum(CompanionGenderEnum), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    rate_per_hour = db.Column(db.Numeric(10, 2), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    languages = db.Column(db.JSON, nullable=True)
    personality_traits = db.Column(db.JSON, nullable=True)
    verification_status = db.Column(db.Enum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    avg_rating = db.Column(db.Numeric(3, 2), nullable=True)
    cover_photo_url = db.Column(db.String(255), nullable=True)

    # Relationships
    photos = db.relationship('CompanionPhoto', backref='companion', lazy=True)
    availabilities = db.relationship('Availability', backref='companion', lazy=True)
    bookings = db.relationship('Booking', backref='companion', lazy=True)
    favorites = db.relationship('Favorite', backref='companion', lazy=True)

    def update_avg_rating(self):
        from models.reviews import Review, ReviewStatusEnum
        from models.bookings import Booking
        from sqlalchemy import func
        from decimal import Decimal
        
        avg = db.session.query(func.avg(Review.rating)).join(Booking).filter(
            Booking.companion_id == self.companion_id,
            Review.status == ReviewStatusEnum.APPROVED
        ).scalar()
        
        if avg is not None:
            self.avg_rating = Decimal(str(round(float(avg), 2)))
        else:
            self.avg_rating = Decimal('0.00')
        db.session.commit()