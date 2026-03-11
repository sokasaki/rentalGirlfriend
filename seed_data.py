from app import app, db
from models import (
    Role, User, CustomerProfile, CompanionProfile, CompanionPhoto,
    Availability, Booking, Payment, Review, Favorite, Notification, Report
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, time
import random

def seed_sample_data():
    """Seed comprehensive sample data for testing"""
    with app.app_context():
        print("Starting data seeding...")
        
        # Check if data already exists
        if User.query.count() > 0:
            print("⚠️  Data already exists. Clear database first if you want to reseed.")
            return
        
        # Get roles
        admin_role = Role.query.filter_by(role_name="Admin").first()
        customer_role = Role.query.filter_by(role_name="Customer").first()
        companion_role = Role.query.filter_by(role_name="Companion").first()
        
        if not all([admin_role, customer_role, companion_role]):
            print("❌ Roles not found. Run seed_roles.py first!")
            return
        
        # 1. Create Admin User
        admin = User(
            role_id=admin_role.role_id,
            username="admin",
            email="admin@rentacompanion.com",
            password=generate_password_hash("admin123"),
            phone="+1-555-0000",
            created_at=datetime.now() - timedelta(days=365)
        )
        db.session.add(admin)
        print("✓ Admin user created")
        
        # 2. Create Customer Users
        customers_data = [
            {"username": "johndoe", "name": "John Doe", "email": "john@email.com", "phone": "+1-555-0101", "dob": "1990-05-15", "gender": "MALE", "location": "New York, NY"},
            {"username": "michalsmith", "name": "Michael Smith", "email": "michael@email.com", "phone": "+1-555-0102", "dob": "1988-08-22", "gender": "MALE", "location": "Los Angeles, CA"},
            {"username": "davidwilson", "name": "David Wilson", "email": "david@email.com", "phone": "+1-555-0103", "dob": "1992-03-10", "gender": "MALE", "location": "Chicago, IL"},
            {"username": "lisaanderson", "name": "Lisa Anderson", "email": "lisa@email.com", "phone": "+1-555-0104", "dob": "1991-12-05", "gender": "FEMALE", "location": "Miami, FL"},
        ]
        
        customers = []
        for cust_data in customers_data:
            user = User(
                role_id=customer_role.role_id,
                username=cust_data["username"],
                email=cust_data["email"],
                password=generate_password_hash("password123"),
                phone=cust_data["phone"],
                created_at=datetime.now() - timedelta(days=random.randint(30, 180))
            )
            db.session.add(user)
            db.session.flush()
            
            profile = CustomerProfile(
                user_id=user.user_id,
                full_name=cust_data["name"],
                date_of_birth=datetime.strptime(cust_data["dob"], "%Y-%m-%d").date(),
                gender=cust_data["gender"],
                bio=f"Hi, I'm {cust_data['name'].split()[0]}. Looking for great companions to spend quality time with!",
                location=cust_data["location"],
                profile_photo="https://i.pravatar.cc/150?img=" + str(random.randint(10, 30))
            )
            db.session.add(profile)
            customers.append(user)
        
        print(f"✓ {len(customers)} customers created")
        
        # 3. Create Companion Users
        companions_data = [
            {
                "username": "sarahj", "name": "Sarah Johnson", "email": "sarah@email.com", "phone": "+1-555-0201",
                "dob": "1995-06-20", "age": 28, "gender": "FEMALE",
                "bio": "Friendly and outgoing companion who loves dining, events, and meaningful conversations. Fluent in English and Spanish.",
                "rate": 75.00, "location": "New York, NY",
                "languages": ["English", "Spanish"],
                "traits": ["Outgoing", "Friendly", "Good Listener", "Sophisticated"],
                "status": "APPROVED", "rating": 4.9
            },
            {
                "username": "emmad", "name": "Emma Davis", "email": "emma@email.com", "phone": "+1-555-0202",
                "dob": "1997-03-15", "age": 26, "gender": "FEMALE",
                "bio": "Adventurous and energetic companion. Love outdoor activities, travel, and trying new cuisines.",
                "rate": 80.00, "location": "Los Angeles, CA",
                "languages": ["English", "French"],
                "traits": ["Adventurous", "Energetic", "Friendly", "Down-to-earth"],
                "status": "APPROVED", "rating": 4.8
            },
            {
                "username": "oliviam", "name": "Olivia Martinez", "email": "olivia@email.com", "phone": "+1-555-0203",
                "dob": "1996-09-08", "age": 27, "gender": "FEMALE",
                "bio": "Artistic and intellectual companion. Enjoy museums, theater, and deep conversations about life.",
                "rate": 85.00, "location": "Chicago, IL",
                "languages": ["English", "Spanish", "Italian"],
                "traits": ["Intellectual", "Artistic", "Caring", "Sophisticated"],
                "status": "APPROVED", "rating": 4.7
            },
            {
                "username": "sophial", "name": "Sophia Lee", "email": "sophia@email.com", "phone": "+1-555-0204",
                "dob": "1998-01-25", "age": 25, "gender": "FEMALE",
                "bio": "Calm and relaxed companion. Perfect for quiet dinners, coffee dates, or study sessions.",
                "rate": 70.00, "location": "Seattle, WA",
                "languages": ["English", "Korean"],
                "traits": ["Calm & Relaxed", "Good Listener", "Caring", "Down-to-earth"],
                "status": "APPROVED", "rating": 4.6
            },
            {
                "username": "jessicaw", "name": "Jessica Williams", "email": "jessica@email.com", "phone": "+1-555-0205",
                "dob": "1997-11-12", "age": 25, "gender": "FEMALE",
                "bio": "Fun-loving companion who enjoys parties, concerts, and social events. Always up for a good time!",
                "rate": 75.00, "location": "Miami, FL",
                "languages": ["English"],
                "traits": ["Outgoing", "Humorous", "Energetic", "Friendly"],
                "status": "PENDING", "rating": None
            },
            {
                "username": "amandab", "name": "Amanda Brown", "email": "amanda@email.com", "phone": "+1-555-0206",
                "dob": "1996-07-18", "age": 28, "gender": "FEMALE",
                "bio": "Elegant and sophisticated companion. Experienced in formal events and high-end dining.",
                "rate": 95.00, "location": "Boston, MA",
                "languages": ["English", "French", "German"],
                "traits": ["Sophisticated", "Intellectual", "Elegant", "Good Listener"],
                "status": "PENDING", "rating": None
            },
        ]
        
        companions = []
        for comp_data in companions_data:
            user = User(
                role_id=companion_role.role_id,
                username=comp_data["username"],
                email=comp_data["email"],
                password=generate_password_hash("password123"),
                phone=comp_data["phone"],
                created_at=datetime.now() - timedelta(days=random.randint(60, 300))
            )
            db.session.add(user)
            db.session.flush()
            
            profile = CompanionProfile(
                user_id=user.user_id,
                display_name=comp_data["name"],
                date_of_birth=datetime.strptime(comp_data["dob"], "%Y-%m-%d").date(),
                age=comp_data["age"],
                gender=comp_data["gender"],
                bio=comp_data["bio"],
                rate_per_hour=comp_data["rate"],
                location=comp_data["location"],
                languages=comp_data["languages"],
                personality_traits=comp_data["traits"],
                verification_status=comp_data["status"],
                avg_rating=comp_data["rating"]
            )
            db.session.add(profile)
            companions.append((user, profile))
        
        print(f"✓ {len(companions)} companions created")
        db.session.flush()
        
        # 4. Create Companion Photos
        photo_count = 0
        for user, profile in companions:
            for i in range(random.randint(3, 6)):
                photo = CompanionPhoto(
                    companion_id=profile.companion_id,
                    photo_url=f"https://images.unsplash.com/photo-{random.randint(1500000000000, 1600000000000)}?w=400",
                    is_primary=(i == 0)
                )
                db.session.add(photo)
                photo_count += 1
        
        print(f"✓ {photo_count} companion photos created")
        
        # 5. Create Availability (only for approved companions)
        # Define different availability patterns for each companion
        availability_count = 0
        all_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        
        # Different availability patterns for each companion
        availability_patterns = [
            {"name": "Weekdays Only", "days": ["MON", "WED", "THU", "FRI"]},  # No Tuesday, No Weekend
            {"name": "Weekends + Some Weekdays", "days": ["MON", "TUE", "SAT", "SUN"]},  # Has Tuesday
            {"name": "Full Week", "days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]},  # Available all days
            {"name": "Limited Hours", "days": ["WED", "THU", "FRI"]},  # Only Mid-week
            {"name": "With Weekend", "days": ["MON", "WED", "SAT", "SUN"]},  # No Tuesday
            {"name": "Random Days", "days": random.sample(all_days, random.randint(4, 6))},  # Random
        ]
        
        for idx, (user, profile) in enumerate(companions):
            if profile.verification_status == "APPROVED":
                # Assign availability pattern based on companion index
                pattern = availability_patterns[idx % len(availability_patterns)]
                print(f"  - {profile.display_name}: {pattern['name']} - Days: {', '.join(pattern['days'])}")
                
                for day in pattern['days']:
                    availability = Availability(
                        companion_id=profile.companion_id,
                        day_of_week=day,
                        start_time=time(9, 0),
                        end_time=time(22, 0)
                    )
                    db.session.add(availability)
                    availability_count += 1
        
        print(f"✓ {availability_count} availability slots created")
        db.session.flush()
        
        # 6. Create Bookings
        approved_companions = [c for u, c in companions if c.verification_status == "APPROVED"]
        customer_profiles = CustomerProfile.query.all()
        
        bookings = []
        for i in range(15):
            customer = random.choice(customer_profiles)
            companion = random.choice(approved_companions)
            
            start_date = datetime.now() - timedelta(days=random.randint(1, 60))
            duration = random.choice([2, 3, 4, 5])
            end_date = start_date + timedelta(hours=duration)
            
            status_options = ["COMPLETED", "COMPLETED", "COMPLETED", "PAID", "APPROVED", "PENDING"]
            status = random.choice(status_options)
            
            booking = Booking(
                customer_id=customer.customer_id,
                companion_id=companion.companion_id,
                start_time=start_date,
                end_time=end_date,
                status=status,
                total_price=float(companion.rate_per_hour) * duration,
                meeting_location=f"{random.choice(['Downtown', 'Uptown', 'City Center'])}, {companion.location}"
            )
            db.session.add(booking)
            bookings.append(booking)
        
        print(f"✓ {len(bookings)} bookings created")
        db.session.flush()
        
        # 7. Create Payments
        payment_count = 0
        for booking in bookings:
            booking_status = booking.status.value if hasattr(booking.status, 'value') else str(booking.status)
            if booking_status in ["PAID", "COMPLETED"]:
                payment = Payment(
                    booking_id=booking.booking_id,
                    amount=booking.total_price,
                    method=random.choice(["ABA", "CARD", "WING"]),
                    status="PAID",
                    paid_at=booking.start_time - timedelta(hours=random.randint(1, 48))
                )
                db.session.add(payment)
                payment_count += 1
        
        print(f"✓ {payment_count} payments created")
        
        # 8. Create Reviews
        review_count = 0
        for booking in bookings:
            booking_status = booking.status.value if hasattr(booking.status, 'value') else str(booking.status)
            if booking_status == "COMPLETED" and random.random() > 0.3:  # 70% chance of review
                review = Review(
                    booking_id=booking.booking_id,
                    rating=random.randint(4, 5),
                    comment=random.choice([
                        "Wonderful experience! Highly recommend.",
                        "Great companion, very professional and friendly.",
                        "Had an amazing time, will definitely book again.",
                        "Excellent service, exceeded my expectations.",
                        "Very enjoyable evening, thank you!"
                    ]),
                    created_at=booking.end_time + timedelta(hours=random.randint(2, 72))
                )
                db.session.add(review)
                review_count += 1
        
        print(f"✓ {review_count} reviews created")
        
        # 9. Create Favorites
        favorite_count = 0
        for customer in customer_profiles:
            # Each customer favorites 1-3 companions
            num_favorites = random.randint(1, 3)
            selected_companions = random.sample(approved_companions, min(num_favorites, len(approved_companions)))
            
            for companion in selected_companions:
                favorite = Favorite(
                    customer_id=customer.customer_id,
                    companion_id=companion.companion_id,
                    created_at=datetime.now() - timedelta(days=random.randint(1, 90))
                )
                db.session.add(favorite)
                favorite_count += 1
        
        print(f"✓ {favorite_count} favorites created")
        
        # 10. Create Notifications
        all_users = User.query.all()
        notification_messages = [
            {"title": "Welcome!", "message": "Welcome to RentACompanion! Complete your profile to get started."},
            {"title": "New Booking", "message": "You have a new booking request. Check your dashboard."},
            {"title": "Booking Confirmed", "message": "Your booking has been confirmed. Have a great time!"},
            {"title": "Payment Received", "message": "Payment received successfully. Thank you!"},
            {"title": "New Review", "message": "You received a new 5-star review! Keep up the great work."},
        ]
        
        notification_count = 0
        for user in all_users[:10]:  # Add notifications to first 10 users
            for i in range(random.randint(2, 5)):
                notif_data = random.choice(notification_messages)
                notification = Notification(
                    user_id=user.user_id,
                    title=notif_data["title"],
                    message=notif_data["message"],
                    is_read=random.choice([True, False]),
                    created_at=datetime.now() - timedelta(days=random.randint(0, 30))
                )
                db.session.add(notification)
                notification_count += 1
        
        print(f"✓ {notification_count} notifications created")
        
        # 11. Create Sample Reports
        report_count = 0
        if len(all_users) > 5:
            for i in range(3):
                report = Report(
                    reporter_id=random.choice(all_users).user_id,
                    target_type=random.choice(["USER", "COMPANION", "BOOKING"]),
                    target_id=random.randint(1, 10),
                    reason=random.choice([
                        "Inappropriate behavior during meeting",
                        "Profile contains misleading information",
                        "No-show without cancellation",
                        "Harassment via messages"
                    ]),
                    status="PENDING",
                    created_at=datetime.now() - timedelta(days=random.randint(1, 15))
                )
                db.session.add(report)
                report_count += 1
        
        print(f"✓ {report_count} reports created")
        
        # Commit all changes
        try:
            db.session.commit()
            print("\n" + "="*60)
            print("🎉 SAMPLE DATA SEEDED SUCCESSFULLY!")
            print("="*60)
            print("\n📊 Summary:")
            print(f"   • 1 Admin user")
            print(f"   • {len(customers)} Customers")
            print(f"   • {len(companions)} Companions (4 Approved, 2 Pending)")
            print(f"   • {photo_count} Photos")
            print(f"   • {availability_count} Availability slots")
            print(f"   • {len(bookings)} Bookings")
            print(f"   • {payment_count} Payments")
            print(f"   • {review_count} Reviews")
            print(f"   • {favorite_count} Favorites")
            print(f"   • {notification_count} Notifications")
            print(f"   • {report_count} Reports")
            print("\n🔐 Login Credentials:")
            print("   Admin:     admin / admin123")
            print("   Customer:  johndoe / password123")
            print("   Companion: sarahj / password123")
            print("="*60 + "\n")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error seeding data: {str(e)}")

if __name__ == '__main__':
    seed_sample_data()
