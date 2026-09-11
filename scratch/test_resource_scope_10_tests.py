import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import User
from app.schemas import AdvisorChatRequest
from app.advisor_service import run_grounded_ai_advisor
from seed_db import ensure_demo_users_seeded

db = SessionLocal()
ensure_demo_users_seeded(db)

admin_user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-99").first()

test_questions = [
    ("TEST 1 (ORS only)", "Compare ORS stock between Jatni and Pipli."),
    ("TEST 2 (Insulin only)", "Compare insulin stock between Jatni and Pipli."),
    ("TEST 3 (Paracetamol only)", "Compare paracetamol stock between Jatni and Pipli."),
    ("TEST 4 (Multi-resource stock levels)", "Compare stock levels between Jatni and Pipli."),
    ("TEST 5 (Multi-resource inventory)", "Compare inventory between Jatni and Pipli."),
    ("TEST 6 (Facility medicines)", "What medicines are available at Jatni?"),
    ("TEST 7 (Lowest ORS)", "Which facility has the lowest ORS stock?"),
    ("TEST 8 (Lowest Insulin)", "Which facility has the lowest insulin stock?"),
    ("TEST 9 (Cuttack vs Pipli Multi-resource)", "Compare stock between Cuttack and Pipli."),
    ("TEST 10 (Both Insulin & ORS requested)", "Compare insulin and ORS between Jatni and Pipli.")
]

print("=== EXECUTING ALL 10 RESOURCE SCOPE RUNTIME TESTS ===")

for title, q in test_questions:
    print(f"\n==================================================")
    print(f"{title}: '{q}'")
    print(f"==================================================")
    req = AdvisorChatRequest(message=q)
    res = run_grounded_ai_advisor(req, admin_user, db)
    print("USER-FACING ANSWER:")
    print(res.answer)
    print("\nSEVERITY:", res.severity)

db.close()
