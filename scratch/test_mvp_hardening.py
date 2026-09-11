import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
ADMIN_HEADERS = {
    "Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99",
    "Content-Type": "application/json"
}

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = ADMIN_HEADERS
    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}

def run_tests():
    print("==================================================")
    print("HEALYSIS MVP HARDENING - LIVE RUNTIME API SUITE")
    print("==================================================")

    # 1. Test Forecasts API
    print("\n[1/5] Testing GET /api/v1/forecasts...")
    status_code, forecasts = make_request(f"{BASE_URL}/api/v1/forecasts")
    assert status_code == 200, f"Expected 200, got {status_code}: {forecasts}"
    print(f"SUCCESS: Returned {len(forecasts)} forecast records.")
    
    first_f = forecasts[0]
    print(f"Sample Forecast Record: {first_f['facility_name']} | {first_f['item_name']} ({first_f['item_code']}) | DoC: {first_f['days_of_cover']} | Risk: {first_f['risk_level']}")
    assert "facility_name" in first_f and first_f["facility_name"] is not None, "Missing facility_name in forecast"
    assert "risk_level" in first_f and first_f["risk_level"] is not None, "Missing risk_level in forecast"

    # Find Jatni ORS forecast
    jatni_ors = next((f for f in forecasts if "Jatni" in (f.get("facility_name") or "") and f["item_code"] == "MED-ORS-SACHET"), None)
    jatni_paracetamol = next((f for f in forecasts if "Jatni" in (f.get("facility_name") or "") and f["item_code"] == "MED-PARACET-500MG"), None)

    if jatni_ors:
        print(f"Verified Jatni ORS pre-transfer state: DoC={jatni_ors['days_of_cover']} Days, Stock={jatni_ors['current_stock']}, Risk={jatni_ors['risk_level']}")
    if jatni_paracetamol:
        print(f"Verified Jatni Paracetamol state: DoC={jatni_paracetamol['days_of_cover']} Days, Stock={jatni_paracetamol['current_stock']}, Risk={jatni_paracetamol['risk_level']}")
        assert jatni_paracetamol["risk_level"] == "SAFE", f"Jatni Paracetamol should be SAFE, got {jatni_paracetamol['risk_level']}"

    # 2. Test Recommendations API
    print("\n[2/5] Testing GET /api/v1/recommendations...")
    status_code, recs = make_request(f"{BASE_URL}/api/v1/recommendations")
    assert status_code == 200, f"Expected 200, got {status_code}: {recs}"
    print(f"SUCCESS: Returned {len(recs)} redistribution recommendations.")
    
    pending_rec = next((r for r in recs if r["status"] == "PENDING_HUMAN_APPROVAL"), None)
    assert pending_rec is not None, "No pending recommendation found!"
    print(f"Pending Rec #{pending_rec['id']}: Transfer {pending_rec['recommended_quantity']} {pending_rec['item_code']} from {pending_rec['donor_facility_name']} ({pending_rec['donor_current_stock']} stock) to {pending_rec['recipient_facility_name']} ({pending_rec['recipient_current_stock']} stock)")

    rec_id = pending_rec["id"]
    donor_pre_stock = pending_rec["donor_current_stock"]
    recip_pre_stock = pending_rec["recipient_current_stock"]
    transfer_qty = pending_rec["recommended_quantity"]

    # 3. Test Approval & Atomic Stock Movement
    print(f"\n[3/5] Testing POST /api/v1/recommendations/{rec_id}/action with APPROVE...")
    status_code, action_resp = make_request(
        f"{BASE_URL}/api/v1/recommendations/{rec_id}/action",
        method="POST",
        data={"action": "APPROVE"}
    )
    assert status_code == 200, f"Expected 200, got {status_code}: {action_resp}"
    assert action_resp["status"] == "APPROVED", f"Expected status APPROVED, got {action_resp['status']}"
    print(f"SUCCESS: Recommendation #{rec_id} approved!")
    print(f"Post-approval donor stock: {action_resp['donor_current_stock']} (Expected: {donor_pre_stock - transfer_qty})")
    print(f"Post-approval recipient stock: {action_resp['recipient_current_stock']} (Expected: {recip_pre_stock + transfer_qty})")
    assert action_resp["donor_current_stock"] == donor_pre_stock - transfer_qty, "Donor stock calculation mismatch!"
    assert action_resp["recipient_current_stock"] == recip_pre_stock + transfer_qty, "Recipient stock calculation mismatch!"

    # 4. Test Duplicate Approval Block
    print(f"\n[4/5] Testing Duplicate Approval Prevention on Rec #{rec_id}...")
    dup_status, dup_resp = make_request(
        f"{BASE_URL}/api/v1/recommendations/{rec_id}/action",
        method="POST",
        data={"action": "APPROVE"}
    )
    assert dup_status == 400, f"Expected 400 Bad Request on duplicate approval, got {dup_status}: {dup_resp}"
    print(f"SUCCESS: Duplicate approval blocked cleanly with message: '{dup_resp.get('detail')}'")

    # 5. Test Resources API
    print("\n[5/5] Testing GET /api/v1/resources...")
    status_code, resources = make_request(f"{BASE_URL}/api/v1/resources")
    assert status_code == 200, f"Expected 200, got {status_code}: {resources}"
    print(f"SUCCESS: Returned {len(resources)} inventory resource items.")
    first_r = resources[0]
    print(f"Sample Inventory Item: {first_r['facility_name']} | {first_r['item_name']} ({first_r['item_code']}) | Qty: {first_r['quantity']} {first_r['unit']} | DoC: {first_r['days_of_cover']} | Risk: {first_r['risk_level']}")
    assert "facility_name" in first_r and first_r["facility_name"] is not None, "Missing facility_name in resource"

    # Re-verify Jatni ORS Risk in Forecasts post-transfer
    status_code, post_forecasts = make_request(f"{BASE_URL}/api/v1/forecasts")
    post_jatni_ors = next((f for f in post_forecasts if "Jatni" in (f.get("facility_name") or "") and f["item_code"] == "MED-ORS-SACHET"), None)
    if post_jatni_ors:
        print(f"\nPost-transfer Jatni ORS Risk Level: {post_jatni_ors['risk_level']} (DoC: {post_jatni_ors['days_of_cover']} Days, Stock: {post_jatni_ors['current_stock']})")

    print("\n==================================================")
    print("ALL LIVE RUNTIME MVP HARDENING VERIFICATIONS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
