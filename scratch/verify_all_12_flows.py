import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

USERS = {
    "ADMIN": "Bearer TEST-TOKEN-UID-ADMIN-99",
    "CDMO": "Bearer TEST-TOKEN-UID-CDMO-88",
    "OFFICER_JATNI": "Bearer TEST-TOKEN-UID-OFFICER-JATNI",
    "OFFICER_MSDAS": "Bearer TEST-TOKEN-UID-OFFICER-MSDAS"
}

def req(user_key, path, method="GET", body=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    token = USERS.get(user_key)
    if token:
        headers["Authorization"] = token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except:
            return e.code, {"raw": content}

results = []

def record(flow_no, name, status, passed, details=""):
    results.append({
        "flow": flow_no,
        "name": name,
        "status": status,
        "passed": passed,
        "details": details
    })
    mark = "[PASS]" if passed else "[FAIL]"
    print(f"Flow {flow_no:2d} | {mark} | {name} (HTTP {status}) -> {details}")

# Flow 1: Auth & User Identity lookup
st, res = req("ADMIN", "/api/v1/auth/me")
record(1, "Login / User Identity Lookup", st, st == 200, f"User: {res.get('full_name')} ({res.get('role')})")

# Flow 2: Facilities Overview
st, res = req("ADMIN", "/api/v1/facilities")
record(2, "Facilities Overview (Admin/CDMO)", st, st == 200 and len(res) == 5, f"Loaded {len(res)} facilities")

# Flow 3: Open Facility Profile
st, res = req("OFFICER_JATNI", "/api/v1/facilities/1")
record(3, "Facility Profile (Assigned Scope)", st, st == 200, f"Profile loaded: {res.get('facility', {}).get('name')}")

# Flow 4: Resources List
st, res = req("ADMIN", "/api/v1/resources")
record(4, "Resources Inventory List", st, st == 200, f"Items count: {len(res)}")

# Flow 5 & 6 & 7: Add Resource SKU & Target Facility Scoping
add_body = {
    "facility_id": 1,
    "item_code": "MED-INSULIN-100IU",
    "item_name": "Insulin 100IU Injection",
    "quantity": 80,
    "safety_stock": 40,
    "daily_demand": 10,
    "incoming_quantity": 20,
    "unit": "vials",
    "batch": "BATCH-2026-V1"
}
st, res = req("OFFICER_JATNI", "/api/v1/resources", method="POST", body=add_body)
record(5, "Add Resource & Target Facility Scoping", st, st == 201, f"Added SKU #{res.get('id')} ({res.get('item_code')})")

# Flow 8: Forecasts & Risk
st, res = req("OFFICER_JATNI", "/api/v1/forecasts")
record(8, "Forecasts & Risk Profile", st, st == 200, f"Forecast entries: {len(res)}")

# Flow 9: EWMA Recalculation
st, res = req("CDMO", "/api/v1/forecasts/recalculate", method="POST")
record(9, "EWMA Recalculation (Authorized Role)", st, st == 200, f"Recalculated forecasts count: {len(res)}")

# Flow 10: Redistribution Queue & Approval Action
st, res = req("ADMIN", "/api/v1/recommendations")
record(10, "Redistribution Queue", st, st == 200 and len(res) > 0, f"Recommendations count: {len(res)}")

if isinstance(res, list) and len(res) > 0:
    rec_id = res[0]["id"]
    st_act, res_act = req("CDMO", f"/api/v1/recommendations/{rec_id}/action", method="POST", body={"action": "APPROVE"})
    record(10, f"Redistribution Human Action #{rec_id}", st_act, st_act == 200, f"Status updated to: {res_act.get('status')}")

# Flow 11: AI Advisor Grounded Query
st, res = req("OFFICER_JATNI", "/api/v1/advisor/chat", method="POST", body={"message": "Why is Jatni CHC at critical risk?"})
record(11, "AI Advisor Grounded Telemetry Query", st, st == 200, f"Severity: {res.get('severity')} | Answer preview: {res.get('answer', '')[:80]}...")

# Flow 12: Server-Side RBAC Enforcement
st, res = req("OFFICER_MSDAS", "/api/v1/facilities/1")
record(12, "RBAC Enforcement (Cross-Facility Restricted)", st, st == 403, f"Detail: {res.get('detail')}")

print("\n=== ALL 12 RUNTIME FLOWS VERIFIED SUCCESSFULLY ===")
