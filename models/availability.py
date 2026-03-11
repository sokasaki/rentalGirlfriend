from extensions import db
from enum import Enum

class DayOfWeekEnum(Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"
    SUN = "SUN"

class Availability(db.Model):
    __tablename__ = 'availability'
    availability_id = db.Column(db.Integer, primary_key=True)
    companion_id = db.Column(db.Integer, db.ForeignKey('companion_profiles.companion_id'), nullable=False)
    day_of_week = db.Column(db.Enum(DayOfWeekEnum), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)