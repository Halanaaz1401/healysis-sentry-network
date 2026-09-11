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
    (1, "What is the stock in West Bengal facilities?"),
    (2, "Why is West Bengal at critical risk?"),
    (3, "What is the ORS stock in West Bengal?"),
    (4, "What is the insulin stock in West Bengal?"),
    (5, "Which West Bengal facilities have active alerts?"),
    (6, "Which Odisha facilities are at risk?"),
    (7, "Compare stock between Behala and Pipli."),
    (8, "Compare insulin between Behala and Pipli."),
    (9, "Which facilities have critical ORS risk?"),
    (10, "What should we do about the current stock situation?")
]

print("=== EXECUTING 10 RUNTIME ACCEPTANCE TESTS ===")

for idx, q in test_questions:
    print(f"\n==================================================")
    print(f"TEST {idx}: '{q}'")
    print(f"==================================================")
    req = AdvisorChatRequest(message=q)
    res = run_grounded_ai_advisor(req, admin_user, db)
    print("USER-FACING ANSWER:")
    print(res.answer)
    print("\nSEVERITY:", res.severity)

db.close()
