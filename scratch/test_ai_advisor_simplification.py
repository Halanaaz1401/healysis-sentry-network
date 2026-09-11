import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import User
from app.schemas import AdvisorChatRequest
from app.advisor_service import run_grounded_ai_advisor

db = SessionLocal()
admin_user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-99").first()

questions = [
    "Why is Jatni CHC at critical risk?",
    "Compare stock level between Jatni and Cuttack.",
    "What is the ORS stock at Jatni?",
    "Which facilities are at critical risk?",
    "How many facilities need redistribution?",
    "What should we do about Jatni's ORS shortage?",
    "Show me the facilities with less than 3 days of stock.",
    "Compare stock level between Jatni and Bhubaneswar."
]

for idx, q in enumerate(questions, 1):
    print(f"\n==========================================")
    print(f"QUESTION {idx}: '{q}'")
    print(f"==========================================")
    req = AdvisorChatRequest(message=q)
    res = run_grounded_ai_advisor(req, admin_user, db)
    print("ANSWER:")
    print(res.answer)
    print("\nSEVERITY:", res.severity)
    print("DATA SOURCES:", res.data_sources)
    print("EVIDENCE COUNT:", len(res.evidence))

db.close()
