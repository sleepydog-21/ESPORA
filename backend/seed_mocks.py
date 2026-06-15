import sys
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import auth

def seed():
    db = SessionLocal()
    
    try:
        # Check if mocks already seeded
        if db.query(models.User).filter(models.User.email == "gen_coord@espora.unam.mx").first():
            print("Mocks already exist in the database. Aborting seed to prevent duplicates.")
            return

        print("Seeding Sites...")
        site1 = db.query(models.Site).filter_by(name="FES Iztacala").first()
        if not site1:
            site1 = models.Site(name="FES Iztacala")
            db.add(site1)
            
        site2 = db.query(models.Site).filter_by(name="Facultad de Psicología").first()
        if not site2:
            site2 = models.Site(name="Facultad de Psicología")
            db.add(site2)
            
        db.commit()
        db.refresh(site1)
        db.refresh(site2)

        print("Seeding Users...")
        default_password = auth.get_password_hash("password123")

        # General Coordinator
        gc = models.User(
            email="gen_coord@espora.unam.mx",
            hashed_password=default_password,
            role=models.RoleEnum.GENERAL_COORDINATOR,
            full_name="Coordinadora General ESPORA",
            phone="5551234567"
        )
        db.add(gc)

        # Coordinators
        coord1 = models.User(
            email="coord_iztacala@espora.unam.mx",
            hashed_password=default_password,
            role=models.RoleEnum.COORDINATOR,
            site_id=site1.id,
            full_name="Coord Iztacala",
        )
        coord2 = models.User(
            email="coord_psico@espora.unam.mx",
            hashed_password=default_password,
            role=models.RoleEnum.COORDINATOR,
            site_id=site2.id,
            full_name="Coord Psicologia",
        )
        db.add(coord1)
        db.add(coord2)

        # Therapists
        therapist1 = models.User(
            email="therapist1_iztacala@espora.unam.mx",
            hashed_password=default_password,
            role=models.RoleEnum.THERAPIST,
            site_id=site1.id,
            full_name="Terapeuta Iztacala 1",
        )
        therapist2 = models.User(
            email="therapist2_iztacala@espora.unam.mx",
            hashed_password=default_password,
            role=models.RoleEnum.THERAPIST,
            site_id=site1.id,
            full_name="Terapeuta Iztacala 2",
        )
        therapist3 = models.User(
            email="therapist1_psico@espora.unam.mx",
            hashed_password=default_password,
            role=models.RoleEnum.THERAPIST,
            site_id=site2.id,
            full_name="Terapeuta Psico 1",
        )
        db.add(therapist1)
        db.add(therapist2)
        db.add(therapist3)
        db.commit()

        print("Seeding Participants & Cases...")
        # Create a few participants and cases
        for i in range(1, 6):
            site = site1 if i % 2 == 0 else site2
            therapist = therapist1 if site == site1 else therapist3
            
            p = models.Participant(
                full_name=f"Alumno Paciente {i}",
                student_account=f"31000000{i}",
                email=f"alumno{i}@ciencias.unam.mx",
                phone="5559998888",
                gender="Femenino" if i % 2 == 0 else "Masculino",
                faculty=site.name,
                career="Biologia" if i % 2 == 0 else "Psicologia",
                site_id=site.id
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            
            # Generate anonymous folio
            p.anonymous_folio = f"{site.id:02d}{p.id:05d}"
            db.commit()
            
            # Case
            c = models.Case(
                participant_id=p.id,
                site_id=site.id,
                therapist_id=therapist.id if i <= 3 else None,
                coordinator_id=coord1.id if site == site1 else coord2.id,
                status=models.CaseStatusEnum.ACTIVE if i <= 3 else models.CaseStatusEnum.WAITING,
                intake_source="limesurvey"
            )
            db.add(c)
        
        db.commit()
        print("Database seeded successfully with Mocks!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
