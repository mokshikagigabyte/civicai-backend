from database import authenticate_user
import logging

# Set logging to see what authenticate_user logs
logging.basicConfig(level=logging.INFO)

def test_auth():
    print("Testing auth for gg@gmail.com with gg1234...")
    user = authenticate_user("gg@gmail.com", "gg1234")
    if user:
        print(f"SUCCESS: {user}")
    else:
        print("FAILED: Authentication returned None")

if __name__ == "__main__":
    test_auth()
