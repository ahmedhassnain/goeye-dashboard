import requests

# Test with junaidanwar user
url = "http://localhost:8000/auth/login"
data = {
    "username": "junaidanwar",
    "password": "analyst456"  # Replace with the actual password
}

print(f"Testing login for: {data['username']}")

try:
    response = requests.post(url, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        print("\n✅ Login successful!")
        token = response.json()
        print(f"Token received: {token.get('access_token', 'No token')[:50]}...")
        print(f"Full name: {token.get('full_name')}")
        print(f"Role: {token.get('role')}")
    else:
        print("\n❌ Login failed")
        if response.status_code == 401:
            print("Wrong username or password")
except Exception as e:
    print(f"Error: {e}")
    print("Make sure the FastAPI server is running!")