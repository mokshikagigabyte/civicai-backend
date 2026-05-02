import requests

url = "http://10.234.236.187:8000/legal/search"
headers = {"Content-Type": "application/json"}

# Test 1: Non-motor vehicle query
print("Test 1: General Knowledge Query")
payload1 = {"query": "What is the capital of France?", "enable_web": False}
try:
    response1 = requests.post(url, json=payload1, headers=headers)
    print(f"Status: {response1.status_code}")
    print(f"Response: {response1.json()}")
except Exception as e:
    print(f"Error: {e}")

print("\nTest 2: Motor Vehicle query")
payload2 = {"query": "Penalty for drink and drive in India", "enable_web": False}
try:
    response2 = requests.post(url, json=payload2, headers=headers)
    print(f"Status: {response2.status_code}")
    print(f"Response: {response2.json()}")
except Exception as e:
    print(f"Error: {e}")
