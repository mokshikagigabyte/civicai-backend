from database import get_session, User
import sys

def list_users():
    session = get_session()
    try:
        users = session.query(User).all()
        if users:
            print(f"Total Users: {len(users)}")
            for u in users:
                print(f"- {u.email} ({u.username})")
        else:
            print("No users found in database.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    list_users()
