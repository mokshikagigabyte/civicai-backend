from database import get_session, User
import sys

def fuzzy_check(email_part):
    session = get_session()
    try:
        users = session.query(User).filter(User.email.like(f"%{email_part}%")).all()
        if users:
            print(f"Found {len(users)} similar users:")
            for u in users:
                print(f"- {u.email} ({u.username})")
        else:
            print(f"No users found with part '{email_part}'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fuzzy_check("gg")
