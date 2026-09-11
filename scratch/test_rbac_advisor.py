import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import User, Facility
from app.schemas import AdvisorChatRequest
from app.advisor_service import run_grounded_ai_advisor

db = SessionLocal()

# 1. Facility Officer for Jatni (facility_id=1, Odisha)
officer_jatni = db.query(User).filter(User.firebase_uid == "UID-OFFICER-JATNI").first()

print("=== TEST RBAC: Jatni Officer querying West Bengal ===")
req1 = AdvisorChatRequest(message="What is the stock in West Bengal facilities?")
res1 = run_grounded_ai_advisor(req1, officer_jatni, db)
print("Answer:\n", res1.answer)
print("Severity:", res1.severity)

# 2. Check or create Facility Officer for Behala (facility_id=4, West Bengal)
behala = db.query(Facility).filter(Facility.name.like("%Behala%")).first()
officer_behala = db.query(User).filter(User.facility_id == behala.id).first()
if not officer_behala:
    officer_behala = User(
        firebase_uid="UID-OFFICER-BEHALA",
        email="officer.behala@healysis.gov.in",
        full_name="Dr. S. Roy (Behala)",
        role="FACILITY_OFFICER",
        facility_id=behala.id,
        is_active=True
    )
    db.add(officer_behala)
    db.commit()

print("\n=== TEST RBAC: Behala Officer querying West Bengal ===")
req2 = AdvisorChatRequest(message="What is the stock in West Bengal facilities?")
res2 = run_grounded_ai_advisor(req2, officer_behala, db)
print("Answer:\n", res2.answer)
print("Severity:", res2.severity)

db.close()
