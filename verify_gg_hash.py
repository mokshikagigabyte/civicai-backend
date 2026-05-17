from database import get_session, User
import bcrypt

def verify_gg():
    try:
        with get_session() as session:
            user = session.query(User).filter_by(email="gg@gmail.com").first()
            if user:
                print(f"User: {user.email}")
                print(f"Password Hash in DB: {user.password_hash}")
                
                # Test manually
                password = "gg1234"
                is_valid = bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
                print(f"Manual verification with 'gg1234': {is_valid}") 
            else:
                print("User gg@gmail.com not found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_gg()
