from database import create_user, get_session, ConflictSession, AnalysisResult, User
from datetime import datetime, timedelta

def seed_data():
    print("🌱 Seeding Test Data...")
    
    test_users = [
        {"name": "Rahul Sharma", "email": "rahul@example.com", "username": "rahul_legal", "pass": "rahul123", "gender": "Male", "dob": datetime(1992, 5, 20)},
        {"name": "Priya Patel", "email": "priya@example.com", "username": "priya_law", "pass": "priya123", "gender": "Female", "dob": datetime(1995, 8, 15)},
        {"name": "Amit Kumar", "email": "amit@example.com", "username": "amit_pro", "pass": "amit123", "gender": "Male", "dob": datetime(1988, 12, 10)}
    ]
    
    for u in test_users:
        success, msg = create_user(u['name'], u['email'], u['username'], u['pass'], u['gender'], u['dob'])
        print(f"User {u['email']}: {msg}")
    
    # Add some history for Rahul
    session = get_session()
    rahul = session.query(User).filter_by(email="rahul@example.com").first()
    if rahul:
        # Session 1
        s1 = ConflictSession(
            user_id=rahul.id,
            partyA_statement="A bike hit me from the wrong side at the intersection.",
            partyB_statement="I was just taking a shortcut and didn't see him.",
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        session.add(s1)
        session.flush()
        
        r1 = AnalysisResult(
            session_id=s1.id,
            sentiment_A="Frustrated",
            toxicity_A=0.1,
            violation="Driving in the wrong direction (One Way)",
            section="Section 184 (Dangerous Driving)",
            suggestion="Immediate fine and license suspension for Party B.",
            severity="High"
        )
        session.add(r1)
        
        print(f"✅ History seeded for {rahul.email}")
    
    session.commit()
    session.close()
    print("✨ Seeding Complete!")

if __name__ == "__main__":
    seed_data()
