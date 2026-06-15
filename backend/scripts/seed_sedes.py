import sys
import os

# Add parent dir to path so we can import models and database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal
import models

def seed_sedes():
    sedes = [
        "Facultad de Ciencias, UNAM",
        "Facultad de Ciencias Políticas y Sociales, UNAM",
        "Facultad de Economía, UNAM",
        "Facultad de Enfermería y Obstetricia, UNAM",
        "Facultad de Filosofía y Letras, UNAM",
        "Facultad de Ingeniería, UNAM",
        "Facultad de Odontología, UNAM",
        "Coordinación de Difusión y Cultura, UNAM",
        "Coordinación General de Estudios de Posgrado, UNAM",
        "Instituto de Ecología, UNAM",
        "Instituto de Fisiología Celular, UNAM",
        "Instituto de Ingeniería, UNAM",
        "Instituto de Neurobiología, en Querétaro, UNAM",
        "Campus Morelos, UNAM",
        "Escuela Nacional de Artes Cinematográficas, UNAM",
        "Escuela Nacional de Ciencias de la Tierra, UNAM",
        "Escuela Nacional de Ciencias Forenses, UNAM",
        "Escuela Nacional de Trabajo Social, UNAM",
        "Colegio de Ciencias y Humanidades, Plantel Oriente",
        "Colegio de Ciencias y Humanidades, Plantel Vallejo",
        "Colegio de Ciencias y Humanidades, Plantel Sur",
        "Colegio de Ciencias y Humanidades, Plantel Naucalpan",
        "Colegio de Ciencias y Humanidades, Plantel Azcapotzalco",
        "Escuela Nacional Preparatoria, Plantel 1",
        "Escuela Nacional Preparatoria, Plantel 2",
        "Escuela Nacional Preparatoria, Plantel 3",
        "Escuela Nacional Preparatoria, Plantel 4",
        "Escuela Nacional Preparatoria, Plantel 5",
        "Escuela Nacional Preparatoria, Plantel 6",
        "Escuela Nacional Preparatoria, Plantel 7",
        "Escuela Nacional Preparatoria, Plantel 8",
        "Escuela Nacional Preparatoria, Plantel 9"
    ]

    db = SessionLocal()
    try:
        count = 0
        for name in sedes:
            # Clean up trailing periods or commas
            clean_name = name.strip(' .,')
            
            # Check if it already exists
            existing = db.query(models.Site).filter(models.Site.name == clean_name).first()
            if not existing:
                site = models.Site(name=clean_name)
                db.add(site)
                count += 1
                
        if count > 0:
            db.commit()
            print(f"✅ Se han agregado {count} nuevas sedes a la base de datos de ESPORA.")
        else:
            print("ℹ️ Todas las sedes proporcionadas ya existían en la base de datos.")
            
    except Exception as e:
        print(f"Error al sembrar sedes: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_sedes()
