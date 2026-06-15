import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
import models
import random
from auth import get_password_hash
from datetime import datetime, timedelta

def seed_presentation():
    db = SessionLocal()
    try:
        site = db.query(models.Site).filter_by(name="FES Iztacala").first()
        if not site:
            print("Site FES Iztacala not found")
            return
            
        coord = db.query(models.User).filter_by(email="coord_iztacala@espora.unam.mx").first()
        
        # 1. Ensure 5 therapists for Iztacala
        therapists = db.query(models.User).filter_by(site_id=site.id, role=models.RoleEnum.THERAPIST).all()
        
        therapist_names = ["Dr. Roberto Gómez", "Dra. María Antonieta", "Psic. Carlos Villagrán", "Dra. Florinda Meza", "Dr. Edgar Vivar"]
        
        for i in range(5):
            email = f"therapist_izt_{i}@espora.unam.mx"
            th = db.query(models.User).filter_by(email=email).first()
            if not th:
                th = models.User(
                    email=email,
                    hashed_password=get_password_hash("Espora2026!"),
                    role=models.RoleEnum.THERAPIST,
                    site_id=site.id,
                    is_active=True,
                    full_name=therapist_names[i]
                )
                db.add(th)
        db.commit()
        
        therapists = db.query(models.User).filter_by(site_id=site.id, role=models.RoleEnum.THERAPIST).all()
        
        # 2. Add waitlist students (around 20) with limesurvey summaries and some risk words
        limesurvey_texts = [
            "Paciente indica sentimientos de tristeza profunda y desmotivación en las últimas semanas. Menciona ideación sobre morir.",
            "Reporta niveles altos de estrés debido a la carga académica. Dificultades para dormir y ansiedad.",
            "Problemas de integración y episodios de pánico antes de los exámenes.",
            "Reporta conflictos familiares recurrentes que afectan su desempeño escolar. Siente desesperanza.",
            "El cuestionario sugiere posible riesgo de depresión moderada. Requiere evaluación detallada.",
            "Menciona que quiere lastimar su cuerpo (cortar). Riesgo alto.",
            "Se siente solo y tiene mucha ansiedad por el futuro. A veces piensa en suicidio.",
            "Estrés generalizado y problemas económicos en casa."
        ]
        
        for i in range(300, 320): # 20 waiting students
            p = db.query(models.Participant).filter_by(student_account=f"300000{i}").first()
            if not p:
                summary = random.choice(limesurvey_texts)
                p = models.Participant(
                    full_name=f"Estudiante en Espera {i}",
                    student_account=f"300000{i}",
                    email=f"espera_{i}@unam.mx",
                    phone="55" + str(random.randint(10000000, 99999999)),
                    gender=random.choice(["Femenino", "Masculino"]),
                    faculty=site.name,
                    career="Medicina",
                    site_id=site.id,
                    metadata_json={"resumen_caso": summary} # UI reads participant.metadata_json.resumen_caso
                )
                db.add(p)
                db.commit()
                db.refresh(p)
                p.anonymous_folio = f"{site.id:02d}{p.id:05d}"
                db.commit()
                
                c = models.Case(
                    participant_id=p.id,
                    site_id=site.id,
                    therapist_id=None,
                    coordinator_id=coord.id,
                    status=models.CaseStatusEnum.WAITING,
                    intake_source="limesurvey"
                )
                db.add(c)
        db.commit()
        
        # 3. Add active students for each therapist to generate workload stats
        topics = db.query(models.Topic).all()
        if not topics:
            base_topics = ["Suicidio", "Depresión", "Violencia", "Ansiedad", "Inseguridad", "Problemas Familiares"]
            for t_name in base_topics:
                t = models.Topic(name=t_name, site_id=None, is_active=True)
                db.add(t)
            db.commit()
            topics = db.query(models.Topic).all()
            
        for th in therapists:
            # Assign 2-5 active cases per therapist
            for i in range(random.randint(2, 5)):
                acc = f"40000{th.id}{i}"
                p = db.query(models.Participant).filter_by(student_account=acc).first()
                if not p:
                    p = models.Participant(
                        full_name=f"Paciente Activo {th.id}-{i}",
                        student_account=acc,
                        email=f"activo_{th.id}_{i}@unam.mx",
                        phone="5512345678",
                        gender="Femenino",
                        faculty=site.name,
                        career="Biología",
                        site_id=site.id,
                        metadata_json={"resumen_caso": "Paciente en tratamiento regular."}
                    )
                    db.add(p)
                    db.commit()
                    db.refresh(p)
                    p.anonymous_folio = f"{site.id:02d}{p.id:05d}"
                    db.commit()
                    
                    c = models.Case(
                        participant_id=p.id,
                        site_id=site.id,
                        therapist_id=th.id,
                        coordinator_id=coord.id,
                        status=models.CaseStatusEnum.ACTIVE,
                        intake_source="manual"
                    )
                    db.add(c)
                    db.commit()
                    db.refresh(c)
                    
                    # Generate some appointments for these active cases
                    for apt_i in range(3):
                        apt = models.Appointment(
                            case_id=c.id,
                            therapist_id=th.id,
                            start_time=datetime.utcnow() - timedelta(days=apt_i*7),
                            end_time=datetime.utcnow() - timedelta(days=apt_i*7) + timedelta(hours=1),
                            status="completed" if apt_i > 0 else "scheduled",
                            notes="Notas de evolución simuladas..."
                        )
                        db.add(apt)
                        db.commit()
                        db.refresh(apt)
                        
                        # Add topics to the completed appointments
                        if apt.status == "completed":
                            sel_topics = random.sample(topics, random.randint(1, 3))
                            for st in sel_topics:
                                at = models.AppointmentTopic(appointment_id=apt.id, topic_id=st.id)
                                db.add(at)
                    db.commit()
                    
        print("Presentation data generated successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_presentation()
