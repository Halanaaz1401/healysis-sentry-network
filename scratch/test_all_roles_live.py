import json
import urllib.request
import urllib.error

base_url = "http://127.0.0.1:8000/api/v1"

users = [
    {"name": "System Admin", "token": "Bearer TEST-TOKEN-UID-ADMIN-99", "expected_role": "ADMIN"},
    {"name": "CDMO Director", "token": "Bearer TEST-TOKEN-UID-CDMO-88", "expected_role": "CDMO"},
    {"name": "Jatni Officer", "token": "Bearer TEST-TOKEN-UID-OFFICER-JATNI", "expected_role": "FACILITY_OFFICER"},
    {"name": "Cuttack Officer", "token": "Bearer TEST-TOKEN-UID-OFFICER-MSDAS", "expected_role": "FACILITY_OFFICER"},
]

def req(url, method="GET", token=None, body=None):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

print("=== 1. VERIFY /api/v1/auth/me FOR ALL ROLES ===")
for u in users:
    st, res = req(f"{base_url}/auth/me", token=u["token"])
    print(f"User: {u['name']} | Status: {st} | Role in DB: {res.get('role')} | Facility: {res.get('facility_id')}")

print("\n=== 2. VERIFY FACILITIES ACCESS & RBAC ===")
st, res = req(f"{base_url}/facilities", token=users[0]["token"]) # ADMIN
print(f"ADMIN Facilities count: {len(res) if st==200 else res}")

st, res = req(f"{base_url}/facilities", token=users[2]["token"]) # Jatni Officer
print(f"Jatni Officer Facilities count (Scoped): {len(res) if st==200 else res}")

st, res = req(f"{base_url}/facilities/1", token=users[2]["token"]) # Jatni Officer -> Facility 1 (Allowed)
print(f"Jatni Officer -> Facility 1 Detail: Status {st}")

st, res = req(f"{base_url}/facilities/2", token=users[2]["token"]) # Jatni Officer -> Facility 2 (Forbidden)
print(f"Jatni Officer -> Facility 2 Detail (Expect 403): Status {st} | Detail: {res.get('detail')}")

print("\n=== 3. VERIFY FORECASTS & EWMA RECALCULATION RBAC ===")
st, res = req(f"{base_url}/forecasts", token=users[0]["token"])
print(f"ADMIN GET Forecasts: Status {st} | Count: {len(res) if st==200 else res}")

st, res = req(f"{base_url}/forecasts/recalculate", method="POST", token=users[0]["token"])
print(f"ADMIN Trigger EWMA: Status {st} | Count: {len(res) if st==200 else res}")

st, res = req(f"{base_url}/forecasts/recalculate", method="POST", token=users[2]["token"])
print(f"Officer Trigger EWMA (Expect 403): Status {st} | Detail: {res.get('detail')}")

print("\n=== 4. VERIFY REDISTRIBUTION ENGINE RBAC ===")
st, res = req(f"{base_url}/recommendations/generate", method="POST", token=users[0]["token"])
print(f"ADMIN Run Redistribution: Status {st} | Recommendations Count: {len(res) if st==200 else res}")

st, res = req(f"{base_url}/recommendations/generate", method="POST", token=users[2]["token"])
print(f"Officer Run Redistribution (Expect 403): Status {st} | Detail: {res.get('detail')}")

print("\n=== 5. VERIFY AI ADVISOR CHAT ===")
st, res = req(f"{base_url}/advisor/chat", method="POST", token=users[0]["token"], body={"message": "Why is Jatni CHC at critical risk?"})
print(f"ADMIN AI Advisor Chat: Status {st} | Severity: {res.get('severity')} | Summary: {res.get('summary')}")
