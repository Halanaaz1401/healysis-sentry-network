import sys, os
sys.path.insert(0, os.path.abspath("backend"))
from app.database import SessionLocal
from app.models import User, Facility, Inventory, Forecast, Alert
from app.advisor_tools import get_facility_overview, get_active_alerts, get_forecasts
from app.advisor_service import run_grounded_ai_advisor
from app.schemas import AdvisorChatRequest

db = SessionLocal()
admin_user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-99").first()

print("--- JATNI FACILITY OVERVIEW ---")
ov = get_facility_overview(1, admin_user, db)
print(ov)

print("\n--- JATNI ACTIVE ALERTS ---")
al = get_active_alerts(1, None, admin_user, db)
print(al)

print("\n--- JATNI FORECASTS ---")
fc = get_forecasts(1, None, admin_user, db)
print(fc)

print("\n--- ADVISOR CHAT RESPONSE ---")
req = AdvisorChatRequest(message="Why is Jatni CHC at critical risk?")
resp = run_grounded_ai_advisor(req, admin_user, db)
print("Answer:", resp.answer)
print("Severity:", resp.severity)
print("Evidence:", resp.evidence)
print("Data Sources:", resp.data_sources)
db.close()
