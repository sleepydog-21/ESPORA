import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import random

def fix():
    db = SessionLocal()
    texts = [
        "Siento niveles altos de estrés debido a mi carga académica. A veces tengo ansiedad.",
        "Me he sentido con una tristeza profunda y desmotivación en las últimas semanas.",
        "Tengo problemas para integrarme con mis compañeros y sufro ataques de pánico antes de los exámenes.",
        "Tengo conflictos familiares recurrentes que me están afectando mucho en la escuela. A veces siento desesperanza.",
        "He tenido pensamientos sobre morir y problemas graves de ansiedad.",
        "A veces quiero lastimar mi cuerpo (cortar). Siento que no puedo más.",
        "Me siento solo y tengo mucha ansiedad por mi futuro. A veces pienso en el suicidio.",
        "Tengo un estrés generalizado y muchos problemas económicos en casa, lo que me causa mucha depresión.",
        "Siento mucha desesperanza respecto a mi futuro profesional."
    ]
    
    parts = db.query(models.Participant).all()
    for p in parts:
        meta = p.metadata_json or {}
        meta["resumen_caso"] = random.choice(texts)
        p.limesurvey_summary = meta["resumen_caso"]
        p.metadata_json = dict(meta)
    
    # Check therapists for Iztacala
    iztacala = db.query(models.Site).filter_by(name="FES Iztacala").first()
    if iztacala:
        therapists = db.query(models.User).filter_by(site_id=iztacala.id, role=models.RoleEnum.THERAPIST).all()
        coord = db.query(models.User).filter_by(email="coord_iztacala@espora.unam.mx").first()
        
        for th in therapists:
            active_cases = db.query(models.Case).filter_by(therapist_id=th.id, status=models.CaseStatusEnum.ACTIVE).count()
            if active_cases == 0:
                for i in range(3):
                    acc = f"50000{th.id}{i}"
                    p = db.query(models.Participant).filter_by(student_account=acc).first()
                    if not p:
                        p = models.Participant(
                            full_name=f"Paciente Asignado {th.id}-{i}",
                            student_account=acc,
                            email=f"rescate_{th.id}_{i}@unam.mx",
                            phone="5512345678",
                            gender="Otro",
                            faculty="FES Iztacala",
                            career="Biología",
                            site_id=iztacala.id,
                            metadata_json={"resumen_caso": random.choice(texts)}
                        )
                        db.add(p)
                        db.commit()
                        db.refresh(p)
                        p.anonymous_folio = f"{iztacala.id:02d}{p.id:05d}"
                        
                        c = models.Case(
                            participant_id=p.id,
                            site_id=iztacala.id,
                            therapist_id=th.id,
                            coordinator_id=coord.id,
                            status=models.CaseStatusEnum.ACTIVE,
                            intake_source="manual"
                        )
                        db.add(c)
                        db.commit()
    db.commit()
    db.close()
    print("Data fixed!")

if __name__ == "__main__":
    fix()
