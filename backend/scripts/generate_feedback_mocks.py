import os
import sys
import random
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models

def generate_mocks():
    db = SessionLocal()
    try:
        therapists = db.query(models.User).filter(models.User.role == models.RoleEnum.THERAPIST).all()
        if not therapists:
            print("No therapists found in database!")
            return
            
        print(f"Found {len(therapists)} therapists. Generating weekly feedback mocks...")
        
        # Clear existing feedback mocks for weeks 10-25 of 2026 to avoid duplicates
        db.query(models.TherapistFeedback).filter(
            models.TherapistFeedback.year == 2026,
            models.TherapistFeedback.week.between(10, 25)
        ).delete()
        db.commit()
        
        count = 0
        for therapist in therapists:
            t_email = therapist.email or ""
            for week in range(10, 26):
                if "laura" in t_email:
                    q1 = max(1, min(10, int(8 - (week - 10) * 0.3 + random.randint(-1, 1))))
                    q2 = max(1, min(10, int(5 + (week - 10) * 0.3 + random.randint(-1, 1))))
                elif "diego" in t_email:
                    q1 = max(1, min(10, int(3 + (week - 10) * 0.4 + random.randint(-1, 1))))
                    q2 = max(1, min(10, int(8 - (week - 10) * 0.3 + random.randint(-1, 1))))
                else:
                    q1 = max(1, min(10, int(5 + random.randint(-2, 2))))
                    q2 = max(1, min(10, int(6 + random.randint(-2, 2))))
                    
                fb = models.TherapistFeedback(
                    therapist_id=therapist.id,
                    year=2026,
                    week=week,
                    q1_score=q1,
                    q2_score=q2,
                    submitted_at=datetime.datetime(2026, 3 + (week // 4), (week % 4) * 7 + 1, 12, 0)
                )
                db.add(fb)
                count += 1
                
        db.commit()
        print(f"Successfully generated {count} feedback mock records for weeks 10-25 of 2026!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_mocks()
