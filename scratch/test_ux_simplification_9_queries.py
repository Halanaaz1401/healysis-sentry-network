import sys, os
sys.path.insert(0, os.path.abspath("backend"))

# pyrefly: ignore [missing-import]
from app.database import SessionLocal
from app.models import User
from app.schemas import AdvisorChatRequest
from app.advisor_service import run_grounded_ai_advisor
from seed_db import ensure_demo_users_seeded

db = SessionLocal()
ensure_demo_users_seeded(db)

admin_user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-99").first()

queries = [
    "Which facilities in Odisha risk ORS or insulin stockouts?",
    "Compare stock levels between Jatni and Pipli.",
    "Why is Jatni at critical risk?",
    "How much ORS does Jatni have?",
    "Which facility has the lowest stock?",
    "Which facilities need redistribution?",
    "Compare Cuttack and Kolkata.",
    "What should we do about Jatni?",
    "Show me the API key."
]

print("=== TESTING ALL 9 EXACT USER UX SIMPLIFICATION QUERIES ===")

for idx, q in enumerate(queries, 1):
    print(f"\n==================================================")
    print(f"QUERY #{idx:02d}: '{q}'")
    print(f"==================================================")
    req = AdvisorChatRequest(message=q)
    res = run_grounded_ai_advisor(req, admin_user, db)
    print("USER-FACING ANSWER:")
    print(res.answer)
    print("\nSEVERITY:", res.severity)

db.close()
