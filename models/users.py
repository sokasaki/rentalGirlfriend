from extensions import db
from datetime import datetime
from enum import Enum

class UserStatus(Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def display_name(self):
        # Always return 'Admin' for administrative roles (non-Customer/Companion)
        if self.role and self.role.role_name.lower() not in ['customer', 'companion']:
            return "Admin"
            
        if self.customer_profile:
            return self.customer_profile.full_name
        if self.companion_profile:
            return self.companion_profile.display_name
        return self.username or self.email.split('@')[0]

    # Relationships
    customer_profile = db.relationship('CustomerProfile', backref='user', uselist=False, lazy=True)
    companion_profile = db.relationship('CompanionProfile', backref='user', uselist=False, lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    reports = db.relationship('Report', backref='reporter', lazy=True)