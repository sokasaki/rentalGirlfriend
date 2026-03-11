from extensions import db
from enum import Enum
from datetime import datetime

class TargetTypeEnum(Enum):
    USER = "USER"
    COMPANION = "COMPANION"
    BOOKING = "BOOKING"

class ReportStatusEnum(Enum):
    PENDING = "PENDING"
    AWAITING_INFO = "AWAITING_INFO"
    RESOLVED = "RESOLVED"

class Report(db.Model):
    __tablename__ = 'reports'
    report_id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    target_type = db.Column(db.Enum(TargetTypeEnum), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ReportStatusEnum), default=ReportStatusEnum.PENDING)
    info_requested_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def reporter_profile(self):
        from models.customer_profiles import CustomerProfile
        from models.companion_profiles import CompanionProfile
        
        cp = CustomerProfile.query.filter_by(user_id=self.reporter_id).first()
        if cp:
            return cp
        
        comp = CompanionProfile.query.filter_by(user_id=self.reporter_id).first()
        if comp:
            return comp
        return None

    @property
    def reporter_name(self):
        profile = self.reporter_profile
        if profile:
            if hasattr(profile, 'full_name'):
                return profile.full_name
            if hasattr(profile, 'display_name'):
                return profile.display_name
        
        from models.users import User
        user = User.query.get(self.reporter_id)
        return user.email if user else 'Unknown User'

    @property
    def requested_at(self):
        if self.info_requested_at:
            return self.info_requested_at.strftime('%b %d, %Y at %H:%M')
        return None

    @property
    def created_date(self):
        return self.created_at.strftime('%b %d, %Y')