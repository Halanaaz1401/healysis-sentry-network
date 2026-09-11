import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import Facility, Inventory, Forecast, Alert, Recommendation, Medicine

db = SessionLocal()

print("--- FACILITIES ---")
for f in db.query(Facility).all():
    print(f"ID={f.id} | Name={f.name} | District={f.district} | State={f.state}")

print("\n--- MEDICINES ---")
for m in db.query(Medicine).all():
    print(f"ID={m.id} | Code={m.sku} | Name={m.name} | Unit={m.unit}")

print("\n--- INVENTORY ---")
for i in db.query(Inventory).all():
    fac = db.query(Facility).get(i.facility_id)
    print(f"Fac={fac.name if fac else i.facility_id} | SKU={i.item_code} | Qty={i.quantity} | Unit={i.unit} | Safety={i.safety_stock}")

print("\n--- FORECASTS ---")
for fc in db.query(Forecast).all():
    fac = db.query(Facility).get(fc.facility_id)
    print(f"Fac={fac.name if fac else fc.facility_id} | SKU={fc.item_code} | DoC={fc.days_of_cover} | Risk={fc.risk_level}")

db.close()
