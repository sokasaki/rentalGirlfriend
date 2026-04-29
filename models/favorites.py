from extensions import db
from datetime import datetime

class Favorite(db.Model):
    __tablename__ = 'favorites'
    favorite_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_profiles.customer_id'), nullable=False)
    companion_id = db.Column(db.Integer, db.ForeignKey('companion_profiles.companion_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)