import sys
import os

# Add the parent directory (backend) to the sys path so we can import from database and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
import models
import random

def seed_more_students():
    db = SessionLocal()
    try:
        site1 = db.query(models.Site).filter_by(name="FES Iztacala").first()
        site2 = db.query(models.Site).filter_by(name="Facultad de Psicología").first()

        if not site1 or not site2:
            print("Sites not found. Please run seed_mocks.py first.")
            return

        coord1 = db.query(models.User).filter_by(email="coord_iztacala@espora.unam.mx").first()
        coord2 = db.query(models.User).filter_by(email="coord_psico@espora.unam.mx").first()

        therapist1 = db.query(models.User).filter_by(email="therapist1_iztacala@espora.unam.mx").first()
        therapist2 = db.query(models.User).filter_by(email="therapist2_iztacala@espora.unam.mx").first()
        therapist3 = db.query(models.User).filter_by(email="therapist1_psico@espora.unam.mx").first()

        print("Seeding more participants and cases...")

        # Seed base topics if they don't exist
        base_topics = ["Suicidio", "Depresión", "Violencia", "Ansiedad", "Inseguridad", "Problemas Familiares"]
        for t_name in base_topics:
            t = db.query(models.Topic).filter_by(name=t_name, site_id=None).first()
            if not t:
                new_topic = models.Topic(name=t_name, site_id=None, is_active=True)
                db.add(new_topic)
        db.commit()
        sites = [site1, site2]
        coords = [coord1, coord2]
        therapists = {
            site1.id: [therapist1, therapist2],
            site2.id: [therapist3]
        }

        # Let's generate 10 more students
        for i in range(200, 210):
            for idx, site in enumerate(sites):
                coord = coords[idx]
                site_therapists = therapists[site.id]

                # 50% waiting, 50% active
                is_active = random.choice([True, False])
                therapist = random.choice(site_therapists) if is_active else None

                limesurvey_texts = [
                    "El alumno reporta niveles altos de estrés debido a la carga académica. Menciona dificultades para dormir.",
                    "Paciente indica sentimientos de tristeza profunda y desmotivación en las últimas semanas.",
                    "Señala problemas de integración con sus compañeros y episodios de ansiedad antes de los exámenes.",
                    "Reporta conflictos familiares recurrentes que afectan su desempeño escolar.",
                    "El cuestionario sugiere posible riesgo de depresión moderada. Requiere evaluación detallada."
                ]
                p = models.Participant(
                    full_name=f"Nuevo Alumno {site.name} {i}",
                    student_account=f"4200000{idx}{i}",
                    email=f"nuevo_alumno_{site.id}_{i}@unam.mx",
                    phone="55" + str(random.randint(10000000, 99999999)),
                    gender=random.choice(["Femenino", "Masculino", "Otro"]),
                    faculty=site.name,
                    career="Biología" if site == site1 else "Psicología",
                    site_id=site.id,
                    limesurvey_summary=random.choice(limesurvey_texts)
                )
                db.add(p)
                db.commit()
                db.refresh(p)
                
                p.anonymous_folio = f"{site.id:02d}{p.id:05d}"
                db.commit()

                c = models.Case(
                    participant_id=p.id,
                    site_id=site.id,
                    therapist_id=therapist.id if therapist else None,
                    coordinator_id=coord.id,
                    status=models.CaseStatusEnum.ACTIVE if is_active else models.CaseStatusEnum.WAITING,
                    intake_source="limesurvey"
                )
                db.add(c)
        
        db.commit()
        print("Successfully generated more students for both sites!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_more_students()
