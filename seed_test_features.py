from app import app, db
from models import User, CompanionProfile, Payout, PayoutStatusEnum, Review, ReviewStatusEnum, SystemSetting, Booking, Payment, PaymentStatusEnum
from datetime import datetime, timedelta
import random

def seed_test_features():
    with app.app_context():
        print("Seeding test data for Payouts, Reviews, and Settings...")
        
        # 1. Ensure System Settings exist
        if not SystemSetting.query.filter_by(key='platform_name').first():
            db.session.add(SystemSetting(key='platform_name', value='RentACompanion', description='Platform Display Name'))
        if not SystemSetting.query.filter_by(key='platform_fee').first():
            db.session.add(SystemSetting(key='platform_fee', value='15', description='Platform Commission Fee (%)'))
        
        # 2. Get some companions to create payouts and reviews for
        companions = CompanionProfile.query.all()
        if not companions:
            print("No companions found. Please run seed_data.py first.")
            return

        # 3. Seed Pending Reviews
        # Find bookings that don't have reviews yet or create new ones
        bookings = Booking.query.limit(5).all()
        for i, booking in enumerate(bookings):
            # Check if review exists
            existing_review = Review.query.filter_by(booking_id=booking.booking_id).first()
            if not existing_review:
                review = Review(
                    booking_id=booking.booking_id,
                    rating=random.randint(4, 5),
                    comment=f"Great experience {i+1}! Testing moderation system.",
                    status=ReviewStatusEnum.PENDING,
                    created_at=datetime.utcnow() - timedelta(days=i)
                )
                db.session.add(review)
                print(f"Added pending review for booking #{booking.booking_id}")

        # 4. Seed Pending Payouts
        for i in range(3):
            comp = random.choice(companions)
            payout = Payout(
                companion_id=comp.companion_id,
                amount=random.uniform(50, 200),
                status=PayoutStatusEnum.PENDING,
                requested_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                reference=f"TEST-PAY-{random.randint(1000, 9999)}"
            )
            db.session.add(payout)
            print(f"Added pending payout for {comp.display_name}")

        db.session.commit()
        print("✅ Testing data seeded successfully!")

if __name__ == '__main__':
    seed_test_features()
