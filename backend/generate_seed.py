import os
import hashlib
import pandas as pd

os.makedirs("data", exist_ok=True)

def create_hash(prev: str, facility: str, item: str, qty: int, action: str, token: str) -> str:
    serialized = f"{prev}|{facility}|{item}|{qty}|{action}|{token or 'ANON'}"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

facilities = [
    {"facility_id": "CHC-OD-KHU-001", "facility_name": "Jatni CHC (Khordha)", "state_id": "OD"},
    {"facility_id": "UPHC-OD-CTC-002", "facility_name": "UPHC MS Das (Kafla Bazar)", "state_id": "OD"},
    {"facility_id": "PHC-OD-PURI-004", "facility_name": "Pipili PHC (Puri)", "state_id": "OD"},
    {"facility_id": "UPHC-WB-KOL-012", "facility_name": "Behala Urban PHC (Kolkata)", "state_id": "WB"},
    {"facility_id": "PHC-WB-S24P-008", "facility_name": "Diamond Harbour PHC", "state_id": "WB"}
]

items = ["MED-INSULIN-100IU", "MED-AMOX-500MG", "MED-ORS-PKT", "MED-PARACET-500MG"]

records = []
prev_hash = "GENESIS_ROOT_HEALYSIS_000"

# Generate 50 realistic baseline historical records
for i in range(1, 51):
    f = facilities[i % len(facilities)]
    item = items[i % len(items)]
    qty = 2 + (i % 5)
    footfall = 16 + (i % 28)
    beds = 10 - (i % 4)
    action = "DISPENSE" if i % 4 != 0 else "RECEIVE"
    token = f"PAT-IN-{8000 + i}" if action == "DISPENSE" else ""
    
    current_hash = create_hash(prev_hash, f["facility_id"], item, qty, action, token)
    
    records.append({
        "event_id": f"EVT-{1000 + i}",
        "facility_id": f["facility_id"],
        "facility_name": f["facility_name"],
        "state_id": f["state_id"],
        "timestamp": f"2026-08-2{ (i % 3) + 1 }T10:{10 + (i % 45):02d}:00Z",
        "action_type": action,
        "item_id": item,
        "quantity": qty,
        "patient_footfall": footfall,
        "bed_occupancy": beds,
        "patient_token": token,
        "reporter_id": f"STAFF-{(i % 4) + 101}",
        "prev_hash": prev_hash,
        "current_hash": current_hash,
        "is_flagged": False,
        "severity": "LOW",
        "violations": ""
    })
    prev_hash = current_hash

# Pre-seeded deliberate anomalies for live demo verification
anomalies = [
    {
        "event_id": "EVT-1051",
        "facility_id": "UPHC-OD-CTC-002",
        "facility_name": "UPHC MS Das (Kafla Bazar)",
        "state_id": "OD",
        "timestamp": "2026-08-23T09:30:00Z",
        "action_type": "DISPENSE",
        "item_id": "MED-INSULIN-100IU",
        "quantity": 55,
        "patient_footfall": 2,
        "bed_occupancy": 3,
        "patient_token": "",
        "reporter_id": "STAFF-103",
        "is_flagged": True,
        "severity": "CRITICAL",
        "violations": "RULE_GHOST_DISPENSE: Critical stock drawdown without valid patient encounter token.; RULE_FOOTFALL_MISMATCH: Outlier draw (55 units) registered against minimal footfall (2 patients)."
    },
    {
        "event_id": "EVT-1052",
        "facility_id": "UPHC-WB-KOL-012",
        "facility_name": "Behala Urban PHC (Kolkata)",
        "state_id": "WB",
        "timestamp": "2026-08-23T11:45:00Z",
        "action_type": "SPOILAGE",
        "item_id": "MED-INSULIN-100IU",
        "quantity": 42,
        "patient_footfall": 32,
        "bed_occupancy": 6,
        "patient_token": "",
        "reporter_id": "STAFF-105",
        "is_flagged": True,
        "severity": "HIGH",
        "violations": "RULE_SPOILAGE_SPIKE: Cold-chain batch loss (42 units) exceeds permissible threshold."
    }
]

for anom in anomalies:
    anom["prev_hash"] = prev_hash
    anom["current_hash"] = create_hash(prev_hash, anom["facility_id"], anom["item_id"], anom["quantity"], anom["action_type"], anom["patient_token"])
    prev_hash = anom["current_hash"]
    records.append(anom)

df = pd.DataFrame(records)
df.to_csv("data/phc_stock_events.csv", index=False)
print(f"SUCCESS: {len(records)} realistic records created in backend/data/phc_stock_events.csv")