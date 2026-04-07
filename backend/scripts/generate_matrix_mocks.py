import os
import sys
import random
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
import auth

def generate_mocks():
    db = SessionLocal()
    try:
        # SEDES (5 UNAM Sites)
        sedes = ["FES Iztacala", "Facultad de Psicología (CU)", "FES Zaragoza", "ENES Juriquilla", "FES Acatlán"]
        site_objs = {}
        for s in sedes:
            site = db.query(models.Site).filter(models.Site.name == s).first()
            if not site:
                site = models.Site(name=s)
                db.add(site)
                db.commit()
                db.refresh(site)
            site_objs[s] = site

        # THERAPISTS (2 per site)
        therapist_objs = []
        for s in sedes:
            for i in range(1, 3):
                email = f"terapeuta{i}.{s.replace(' ', '').lower()}@espora.unam.mx"
                user = db.query(models.User).filter(models.User.email == email).first()
                if not user:
                    user = models.User(
                        email=email,
                        hashed_password=auth.get_password_hash("test1234"),
                        role=models.RoleEnum.THERAPIST,
                        site_id=site_objs[s].id,
                        is_active=True,
                        full_name=f"Lic. Terapeuta Mock {i} ({s})"
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                therapist_objs.append(user)

        # PARTICIPANTS & CASES (Generate 250 cases spanning 6 months)
        total_cases_to_gen = 250
        print(f"Injecting {total_cases_to_gen} clinic cases...")
        
        statuses = [
            models.CaseStatusEnum.WAITING,
            models.CaseStatusEnum.ACTIVE,
            models.CaseStatusEnum.CLOSED,
            models.CaseStatusEnum.CANCELLED
        ]
        
        for k in range(total_cases_to_gen):
            # Pick random site
            target_site_name = random.choices(sedes, weights=[30, 40, 10, 5, 15])[0] 
            # Iztacala and CU are overloaded intentionally
            
            p = models.Participant(
                student_account=f"31{random.randint(1000000, 9999999)}",
                full_name=f"Estudiante Mock {k}",
                faculty=target_site_name,
                career="Psicología" if random.random() > 0.5 else "Derecho",
                email=f"alumno.mock{k}@comunidad.unam.mx",
                phone="55" + str(random.randint(10000000, 99999999))
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            
            target_status = random.choice(statuses)
            
            # Weighted status if overloaded
            if target_site_name in ["FES Iztacala", "Facultad de Psicología (CU)"]:
                if random.random() < 0.6: 
                    target_status = models.CaseStatusEnum.WAITING
                    
            c = models.Case(
                participant_id=p.id,
                site_id=site_objs[target_site_name].id,
                status=target_status,
                intake_source="web_form"
            )
            
            if target_status in [models.CaseStatusEnum.ACTIVE, models.CaseStatusEnum.CLOSED]:
                # Assign a random therapist from that site
                c.therapist_id = random.choice([t.id for t in therapist_objs if t.site_id == site_objs[target_site_name].id])
                
            db.add(c)
            db.commit()
            db.refresh(c)
            
            # Backdate created_at to max 180 days ago
            random_days_ago = random.randint(1, 180)
            mock_date = datetime.utcnow() - timedelta(days=random_days_ago)
            # Update created_at using SQLAlchemy raw update to skip events
            db.query(models.Case).filter(models.Case.id == c.id).update({"created_at": mock_date})
            db.commit()

        print("✅ Mock data generation complete!")

    except Exception as e:
        print("❌ Error generating mocks:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_mocks()
