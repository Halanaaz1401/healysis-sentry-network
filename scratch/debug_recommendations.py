import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import User, UserRole, Recommendation
from app.routers.recommendations import get_all_recommendations

db = SessionLocal()
admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
print("Admin User:", admin_user.email if admin_user else None)

try:
    recs = get_all_recommendations(current_user=admin_user, db=db)
    print("Successfully fetched recommendations count:", len(recs))
    for r in recs:
        print("Rec:", r)
except Exception as e:
    import traceback
    print("EXCEPTION ENCOUNTERED:")
    traceback.print_exc()
finally:
    db.close()
