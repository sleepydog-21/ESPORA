import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from datetime import datetime, timedelta

def seed_sessions():
    db = SessionLocal()
    try:
        # Get therapist 1
        therapist = db.query(models.User).filter_by(email="therapist1_iztacala@espora.unam.mx").first()
        if not therapist:
            print("Therapist not found")
            return
            
        # Get active case for this therapist
        case = db.query(models.Case).filter_by(therapist_id=therapist.id, status=models.CaseStatusEnum.ACTIVE).first()
        if not case:
            print("No active case found for therapist")
            return
            
        print(f"Seeding sessions for Therapist {therapist.id} and Case {case.id}")
        
        # Clear old sessions to avoid duplicates
        db.query(models.Session).filter_by(case_id=case.id).delete()
        
        # Create sessions for today, next week, and the week after
        base_date = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
        
        sessions = [
            models.Session(
                case_id=case.id,
                session_date=base_date,
                status="completed",
                therapist_notes="Sesión inicial. Paciente refiere ansiedad por exámenes."
            ),
            models.Session(
                case_id=case.id,
                session_date=base_date + timedelta(days=7),
                status="scheduled",
                therapist_notes=""
            ),
            models.Session(
                case_id=case.id,
                session_date=base_date + timedelta(days=14),
                status="scheduled",
                therapist_notes=""
            )
        ]
        
        db.add_all(sessions)
        db.commit()
        print("Successfully seeded 3 sessions!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_sessions()
