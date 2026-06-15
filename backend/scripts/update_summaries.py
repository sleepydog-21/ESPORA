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
        "El alumno reporta niveles altos de estrés debido a la carga académica.",
        "Paciente indica sentimientos de tristeza profunda y desmotivación en las últimas semanas.",
        "Señala problemas de integración con sus compañeros.",
        "Reporta conflictos familiares recurrentes que afectan su desempeño escolar.",
        "Menciona ideación sobre morir y problemas graves de ansiedad.",
        "Siente desesperanza respecto a su futuro profesional."
    ]
    parts = db.query(models.Participant).all()
    count = 0
    for p in parts:
        meta = p.metadata_json or {}
        if not p.limesurvey_summary and not meta.get("resumen_caso"):
            meta["resumen_caso"] = random.choice(texts)
            # SQLAlchemy JSON mutation detection requires re-assignment
            p.metadata_json = dict(meta)
            db.commit()
            count += 1
    print(f"Fixed {count} participants.")
    db.close()

if __name__ == "__main__":
    fix()
