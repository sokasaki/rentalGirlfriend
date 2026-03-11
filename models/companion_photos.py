from extensions import db

class CompanionPhoto(db.Model):
    __tablename__ = 'companion_photos'
    photo_id = db.Column(db.Integer, primary_key=True)
    companion_id = db.Column(db.Integer, db.ForeignKey('companion_profiles.companion_id'), nullable=False)
    photo_url = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)