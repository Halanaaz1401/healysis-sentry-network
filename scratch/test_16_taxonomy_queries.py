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

test_queries = [
    ("A. Summary", "Give me a summary of healthcare resource availability across Odisha."),
    ("B. Summary variation", "Give me an overview of healthcare resources in Odisha."),
    ("C. State operational", "How are healthcare supplies looking across West Bengal?"),
    ("D. Risk list", "Which facilities in West Bengal are currently at risk of stockout?"),
    ("E. Risk explanation", "Why is Jatni CHC at risk?"),
    ("F. Resource-specific", "What is the current insulin stock at Pipli PHC?"),
    ("G. Generic resource", "What is the insulin stock across all accessible facilities?"),
    ("H. Facility inventory", "Give me the inventory status of Behala Urban PHC."),
    ("I. Comparison", "Compare stock between Pipli PHC and Jatni CHC."),
    ("J. Geography", "Which district has the highest stockout risk?"),
    ("K. Redistribution", "Which facility can supply a facility currently at risk?"),
    ("L. Ambiguity", "What is the stock?"),
    ("M. Missing data", "What is the stock of a resource that does not exist?"),
    ("N. Multi-constraint", "Which facilities in Odisha have low stock of insulin?"),
    ("O. Overall", "What needs attention right now?"),
    ("P. Operational", "Give me a quick operational picture of all accessible facilities.")
]

print("=== EXECUTING 16 TAXONOMY ACCEPTANCE TESTS ===")

for title, q in test_queries:
    print(f"\n==================================================")
    print(f"{title}: '{q}'")
    print(f"==================================================")
    req = AdvisorChatRequest(message=q)
    res = run_grounded_ai_advisor(req, admin_user, db)
    print("USER-FACING ANSWER:")
    print(res.answer)
    print("\nSEVERITY:", res.severity)

db.close()
