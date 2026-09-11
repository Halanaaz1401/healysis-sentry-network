import urllib.request, json

print("=== CHECKING LIVE SERVER ACCESSIBILITY ===")

# Backend facilities endpoint
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/facilities") as response:
        backend_status = response.status
        backend_body = json.loads(response.read().decode('utf-8'))
        print(f"Backend http://127.0.0.1:8000/api/v1/facilities: HTTP {backend_status} - Found {len(backend_body)} facilities")
except Exception as e:
    print(f"Backend check error: {e}")

# Frontend root
try:
    with urllib.request.urlopen("http://localhost:3000") as response:
        frontend_status = response.status
        print(f"Frontend http://localhost:3000: HTTP {frontend_status}")
except Exception as e:
    print(f"Frontend check error: {e}")
