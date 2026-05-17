from database import create_user, get_session, User
import sys

def force_register():
    email = "gg@gmail.com"
    try:
        with get_session() as session:
            existing = session.query(User).filter_by(email=email).first()
            if existing:
                print(f"User {email} already exists. Updating password...")
                from database import hash_password
                existing.password_hash = hash_password("gg1234")
                print("Password updated to: gg1234")
            else:
                success, msg = create_user(
                    name="GG User",
                    email=email,
                    username="gg_pro",
                    password="gg1234"
                )
                if success:
                    print(f"User {email} created successfully with password: gg1234")
                else:
                    print(f"Failed to create user: {msg}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    force_register()
