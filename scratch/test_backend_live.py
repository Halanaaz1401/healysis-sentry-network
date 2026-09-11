import urllib.request
import json

headers = {
    "Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99",
    "Content-Type": "application/json"
}

endpoints = [
    "http://localhost:8000/",
    "http://localhost:8000/api/v1/alerts",
    "http://localhost:8000/api/v1/forecasts",
    "http://localhost:8000/api/v1/recommendations",
]

for url in endpoints:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"=== {url} ===")
            print(f"Status: {resp.status}")
            if isinstance(data, list):
                print(f"Items count: {len(data)}")
                for item in data[:2]:
                    print("  Sample item:", json.dumps(item, indent=2))
            else:
                print("  Data:", data)
    except Exception as e:
        print(f"=== {url} ERROR ===")
        print(e)
