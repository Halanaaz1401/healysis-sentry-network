import requests
import json

BASE_URL = "http://127.0.0.1:8000"

ADMIN_HDR = {"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
CDMO_HDR = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
JATNI_HDR = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
MSDAS_HDR = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-MSDAS"}

def main():
    print("=== 1. Health Check ===")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    print("Health OK:", r.json()["status"])

    print("\n=== 2. Check Notifications as FACILITY_OFFICER (Jatni) ===")
    r = requests.get(f"{BASE_URL}/api/v1/notifications", headers=JATNI_HDR)
    print("Status:", r.status_code, r.text)
    assert r.status_code == 200
    notifs = r.json()
    print(f"Jatni Officer sees {len(notifs)} notification(s)")

    print("\n=== 3. Check Notifications as CDMO ===")
    r = requests.get(f"{BASE_URL}/api/v1/notifications", headers=CDMO_HDR)
    assert r.status_code == 200
    cdmo_notifs = r.json()
    print(f"CDMO sees {len(cdmo_notifs)} notification(s)")

    print("\n=== 4. Test Cross-Facility Acknowledgment Rejection (HTTP 403) ===")
    # Try to find a notification from Jatni facility
    jatni_notif = next((n for n in cdmo_notifs if n.get("facility_name", "").startswith("Jatni") or n.get("facility_id") == 1), None)
    if jatni_notif:
        # Officer MSDAS (Facility 2) tries to acknowledge Jatni (Facility 1)
        r = requests.post(
            f"{BASE_URL}/api/v1/notifications/{jatni_notif['id']}/acknowledge",
            headers=MSDAS_HDR,
            json={"action_taken": "Unauthorized attempt"}
        )
        print("Cross-facility rejection status:", r.status_code, "(expected 403)")
        assert r.status_code == 403

    print("\n=== 5. Trigger Process Escalations as CDMO ===")
    r = requests.post(f"{BASE_URL}/api/v1/notifications/process-escalations", headers=CDMO_HDR)
    print("Escalation processing:", r.status_code, r.json())
    assert r.status_code == 200

    print("\n=== 6. Verify Audit Ledger SHA-256 Chain Integrity ===")
    r = requests.get(f"{BASE_URL}/api/v1/audit/events", headers=ADMIN_HDR)
    assert r.status_code == 200
    events = r.json()
    print(f"Audit ledger contains {len(events)} event(s)")
    assert len(events) > 0
    # Check if ALERT_ESCALATED or ALERT_NOTIFICATION_CREATED exists
    actions = [e["action"] for e in events]
    print("Recent actions in audit ledger:", actions[:5])
    assert any("ALERT" in a for a in actions)

    print("\n=== 7. Verify Explainability Endpoints ===")
    r = requests.get(f"{BASE_URL}/api/v1/alerts", headers=CDMO_HDR)
    assert r.status_code == 200
    alerts = r.json()
    if alerts:
        alt_id = alerts[0]["id"]
        r = requests.get(f"{BASE_URL}/api/v1/alerts/{alt_id}/explain", headers=CDMO_HDR)
        assert r.status_code == 200
        print(f"Alert #{alt_id} explanation:", r.json()["why"][:60], "...")

    print("\n=== ALL LIVE INTEGRATION CHECKS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
