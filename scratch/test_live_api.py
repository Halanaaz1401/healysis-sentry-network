import json
import urllib.request
import urllib.error

base_url = "http://127.0.0.1:8000/api/v1"
headers = {
    "Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99",
    "Content-Type": "application/json"
}

def test_endpoint(name, url, method="GET", body=None):
    print(f"\n--- TESTING {name}: {method} {url} ---")
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            print(f"STATUS: {status}")
            print(f"RESPONSE: {content[:400]}")
            return status, json.loads(content) if content else None
    except urllib.error.HTTPError as e:
        status = e.code
        content = e.read().decode("utf-8")
        print(f"STATUS: {status}")
        print(f"ERROR BODY: {content}")
        return status, json.loads(content) if content else None

# Test AI Advisor Chat
test_endpoint("POST AI Advisor Chat", f"{base_url}/advisor/chat", method="POST", body={
    "message": "Why is Jatni CHC at critical risk?"
})
