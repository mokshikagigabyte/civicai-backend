from database import get_session, User
import sys

def check_user(email):
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if user:
            print(f"User FOUND: {user.email}")
            print(f"Name: {user.name}")
            print(f"Username: {user.username}")
        else:
            print(f"User NOT FOUND: {email}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_user("gg@gmail.com")
