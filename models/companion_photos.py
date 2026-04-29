from extensions import db

class CompanionPhoto(db.Model):
    __tablename__ = 'companion_photos'
    photo_id = db.Column(db.Integer, primary_key=True)
    companion_id = db.Column(db.Integer, db.ForeignKey('companion_profiles.companion_id'), nullable=False)
    photo_url = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)

    @property
    def thumbnail_url(self):
        if not self.photo_url:
            return None
        if self.photo_url.startswith(('http://', 'https://', '//', '/static/')) or '://' in self.photo_url:
            return self.photo_url
        
        import os
        directory, filename = os.path.split(self.photo_url.lstrip('/'))
        return f"/static/{directory}/thumb_{filename}"

    @property
    def main_url(self):
        if not self.photo_url:
            return None
        if self.photo_url.startswith(('http://', 'https://', '//', '/static/')) or '://' in self.photo_url:
            return self.photo_url
            
        import os
        directory, filename = os.path.split(self.photo_url.lstrip('/'))
        return f"/static/{directory}/resized_{filename}"