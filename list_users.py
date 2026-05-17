from database import get_session, User
import sys

def list_users():
    try:
        with get_session() as session:
            users = session.query(User).all()
            if users:
                print(f"Total Users: {len(users)}")
                for u in users:
                    print(f"- {u.email} ({u.username})")
            else:
                print("No users found in database.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_users()
