import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

USERS = {
    "ADMIN": "Bearer TEST-TOKEN-UID-ADMIN-99",
    "CDMO": "Bearer TEST-TOKEN-UID-CDMO-88",
    "OFFICER_JATNI": "Bearer TEST-TOKEN-UID-OFFICER-JATNI",
    "OFFICER_MSDAS": "Bearer TEST-TOKEN-UID-OFFICER-MSDAS",
    "NO_TOKEN": None,
    "INVALID_TOKEN": "Bearer INVALID-XYZ-TOKEN"
}

def test_req(user_key, path, method="GET", body=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    token = USERS.get(user_key)
    if token:
        headers["Authorization"] = token
    
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except:
            return e.code, {"raw": content}
    except Exception as exc:
        return 0, {"error": str(exc)}

print("=== 1. TESTING FACILITIES ENDPOINTS ===")
for path in ["/facilities", "/api/v1/facilities", "/api/v1/facilities/"]:
    for u in ["ADMIN", "OFFICER_JATNI", "NO_TOKEN"]:
        st, res = test_req(u, path)
        print(f"[{u}] {path} -> {st} | {str(res)[:100]}")

print("\n=== 2. TESTING FACILITY PROFILE ENDPOINTS ===")
for fid in [1, 2, 999]:
    for u in ["ADMIN", "OFFICER_JATNI", "OFFICER_MSDAS"]:
        path = f"/api/v1/facilities/{fid}"
        st, res = test_req(u, path)
        print(f"[{u}] GET {path} -> {st} | {str(res)[:120]}")

print("\n=== 3. TESTING RESOURCES & ADD RESOURCE ===")
st_cat, res_cat = test_req("ADMIN", "/api/v1/resources/catalog")
print(f"Catalog -> {st_cat} | count={len(res_cat) if isinstance(res_cat, list) else 0}")
st_res, res_r = test_req("ADMIN", "/api/v1/resources")
print(f"Resources -> {st_res} | count={len(res_r) if isinstance(res_r, list) else 0}")

# Test Add Resource POST payload as sent by frontend
add_body = {
    "facility_id": 1,
    "item_code": "MED-ORS-SACHET",
    "item_name": "ORS Sachet (Oral Rehydration Salts)",
    "quantity": 100,
    "safety_stock": 40,
    "daily_demand": 15,
    "incoming_quantity": 0,
    "unit": "sachets",
    "batch": "BATCH-2026-N1"
}
for u in ["ADMIN", "OFFICER_JATNI", "OFFICER_MSDAS"]:
    st_post, res_post = test_req(u, "/api/v1/resources", method="POST", body=add_body)
    print(f"[{u}] POST /api/v1/resources -> {st_post} | {str(res_post)[:150]}")

print("\n=== 4. TESTING FORECASTS ===")
for u in ["ADMIN", "OFFICER_JATNI"]:
    st, res = test_req(u, "/api/v1/forecasts")
    print(f"[{u}] GET /api/v1/forecasts -> {st} | count={len(res) if isinstance(res, list) else res}")

st_recalc, res_recalc = test_req("ADMIN", "/api/v1/forecasts/recalculate", method="POST")
print(f"[ADMIN] POST /api/v1/forecasts/recalculate -> {st_recalc} | count={len(res_recalc) if isinstance(res_recalc, list) else res_recalc}")

st_recalc_off, res_recalc_off = test_req("OFFICER_JATNI", "/api/v1/forecasts/recalculate", method="POST")
print(f"[OFFICER_JATNI] POST /api/v1/forecasts/recalculate -> {st_recalc_off} | {res_recalc_off}")

print("\n=== 5. TESTING REDISTRIBUTION ===")
for u in ["ADMIN", "OFFICER_JATNI", "INVALID_TOKEN"]:
    st, res = test_req(u, "/api/v1/recommendations")
    print(f"[{u}] GET /api/v1/recommendations -> {st} | count={len(res) if isinstance(res, list) else res}")

print("\n=== 6. TESTING AI ADVISOR ===")
for u in ["ADMIN", "OFFICER_JATNI", "INVALID_TOKEN"]:
    st, res = test_req(u, "/api/v1/advisor/chat", method="POST", body={"message": "Why is Jatni CHC at critical risk?"})
    print(f"[{u}] POST /api/v1/advisor/chat -> {st} | answer={res.get('answer','')[:100] if isinstance(res, dict) else res}")
