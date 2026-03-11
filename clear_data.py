from app import app, db
from models import (
    Role, User, CustomerProfile, CompanionProfile, CompanionPhoto,
    Availability, Booking, Payment, Review, Favorite, Notification, Report
)

def clear_database():
    """Clear all data from database (except roles)"""
    with app.app_context():
        try:
            print("Clearing database...")
            
            # Delete in reverse order of dependencies
            Report.query.delete()
            Notification.query.delete()
            Favorite.query.delete()
            Review.query.delete()
            Payment.query.delete()
            Booking.query.delete()
            Availability.query.delete()
            CompanionPhoto.query.delete()
            CompanionProfile.query.delete()
            CustomerProfile.query.delete()
            User.query.delete()
            # Keep roles
            
            db.session.commit()
            print("✓ Database cleared successfully!")
            print("  Roles are preserved for reseeding.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing database: {str(e)}")

if __name__ == '__main__':
    clear_database()
