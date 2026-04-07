import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine, Base
import models
import auth

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Checking/Seeding Site...")
        site1 = db.query(models.Site).filter_by(name="Odontología").first()
        if not site1:
            site1 = models.Site(name="Odontología")
            db.add(site1)
            db.commit()
            db.refresh(site1)
            
        site2 = db.query(models.Site).filter_by(name="Ciencias").first()
        if not site2:
            site2 = models.Site(name="Ciencias")
            db.add(site2)
            db.commit()
            db.refresh(site2)

        print("Checking/Seeding Users...")
        admin = db.query(models.User).filter_by(email="admin@espora.unam.mx").first()
        if not admin:
            admin = models.User(
                email="admin@espora.unam.mx",
                hashed_password=auth.get_password_hash("admin123"),
                role=models.RoleEnum.ADMIN,
                site_id=None
            )
            db.add(admin)

        coord = db.query(models.User).filter_by(email="coord@espora.unam.mx").first()
        if not coord:
            coord = models.User(
                email="coord@espora.unam.mx",
                hashed_password=auth.get_password_hash("coord123"),
                role=models.RoleEnum.COORDINATOR,
                site_id=site1.id
            )
            db.add(coord)
            
        coord2 = db.query(models.User).filter_by(email="coord2@espora.unam.mx").first()
        if not coord2:
            coord2 = models.User(
                email="coord2@espora.unam.mx",
                hashed_password=auth.get_password_hash("coord123"),
                role=models.RoleEnum.COORDINATOR,
                site_id=site2.id
            )
            db.add(coord2)

        therapist_base = db.query(models.User).filter_by(email="laura.martinez@espora.unam.mx").first()
        if not therapist_base:
            therapist_base = models.User(
                email="laura.martinez@espora.unam.mx",
                hashed_password=auth.get_password_hash("terapeuta123"),
                role=models.RoleEnum.THERAPIST,
                site_id=site1.id
            )
            db.add(therapist_base)
            
        therapist_2 = db.query(models.User).filter_by(email="diego.fernandez@espora.unam.mx").first()
        if not therapist_2:
            therapist_2 = models.User(
                email="diego.fernandez@espora.unam.mx",
                hashed_password=auth.get_password_hash("terapeuta123"),
                role=models.RoleEnum.THERAPIST,
                site_id=site1.id
            )
            db.add(therapist_2)

        therapist_3 = db.query(models.User).filter_by(email="sofia.ramirez@espora.unam.mx").first()
        if not therapist_3:
            therapist_3 = models.User(
                email="sofia.ramirez@espora.unam.mx",
                hashed_password=auth.get_password_hash("terapeuta123"),
                role=models.RoleEnum.THERAPIST,
                site_id=site1.id
            )
            db.add(therapist_3)
            
        db.commit()
        db.refresh(therapist_base)
        db.refresh(therapist_2)
        db.refresh(therapist_3)

        print("Seeding Mocks...")
        mocks = [
            {"name": "Juan Perez", "account": "315000001", "email": "juan.perez@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Siento mucha ansiedad constante, especialmente antes de mis exámenes. A veces pienso que sería mejor si me muriera para no sentir esta presión. No puedo dormir bien."},
            {"name": "Ana Sofia Ramos", "account": "315000002", "email": "ana.ramos@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Me he sentido muy triste las últimas semanas. Terminé con mi pareja y problemas familiares me están afectando mucho. Siento desesperanza pero trato de salir adelante."},
            {"name": "Carlos Gomez", "account": "315000003", "email": "carlos.gomez@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Quisiera agendar una cita porque me cuesta mucho trabajo concentrarme y tengo problemas de procrastinación. Necesito ayuda para organizarme mejor."},
            {"name": "Maria Fernanda Lopez", "account": "315000004", "email": "mafer.lopez@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Tengo ataques de pánico repentinos. Siento que me falta la respiración y el corazón me late muy rápido. Siento mucho miedo a morir o volverme loca en esos momentos."},
            {"name": "Diego Hernandez", "account": "315000005", "email": "diego.hernandez@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Solo quiero saber si me pueden ayudar con orientación vocacional porque creo que me equivoqué de carrera."},
            {"name": "Laura Martinez", "account": "315000006", "email": "laura.martinez@alumno.unam.mx", "status": models.CaseStatusEnum.ASSIGNED, "therapist": therapist_base.id, "resumen": "Problemas de adaptación social en la universidad, me siento muy aislada."},
            {"name": "Roberto Torres", "account": "315000007", "email": "roberto.torres@alumno.unam.mx", "status": models.CaseStatusEnum.ACTIVE, "therapist": therapist_base.id, "resumen": "Pérdida de un familiar recietemente, necesito acompañamiento."},
            {"name": "Elena Morales", "account": "315000008", "email": "elena.morales@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Últimamente me corto los brazos cuando me siento mal. Tengo pensamientos de lastimarme recurrentes."},
            {"name": "Luis Vega", "account": "315000009", "email": "luis.vega@alumno.unam.mx", "status": models.CaseStatusEnum.WAITING, "therapist": None, "resumen": "Me siento muy cansado, una depresion profunda que no me deja levantarme de la cama."},
            {"name": "Sofia Castillo", "account": "315000010", "email": "sofia.castillo@alumno.unam.mx", "status": models.CaseStatusEnum.ASSIGNED, "therapist": therapist_2.id, "resumen": "Estrés post-traumático debido a un asalto reciente."},
            {"name": "Raul Diaz", "account": "315000011", "email": "raul.diaz@alumno.unam.mx", "status": models.CaseStatusEnum.ACTIVE, "therapist": therapist_3.id, "resumen": "Dificultades de pareja graves que están afectando mi rendimiento escolar."},
        ]
        
        for mock in mocks:
            participant = db.query(models.Participant).filter_by(student_account=mock["account"]).first()
            if not participant:
                participant = models.Participant(
                    full_name=mock["name"],
                    student_account=mock["account"],
                    email=mock["email"],
                    phone="5550000000",
                    site_id=site1.id,
                    metadata_json={"resumen_caso": mock["resumen"]}
                )
                db.add(participant)
                db.commit()
                db.refresh(participant)
                
                case_assigned = mock["therapist"]
                case = models.Case(
                    participant_id=participant.id,
                    site_id=site1.id,
                    status=mock["status"],
                    therapist_id=case_assigned,
                    intake_source="limesurvey"
                )
                db.add(case)
                db.commit()
            else:
                participant.metadata_json = {"resumen_caso": mock["resumen"]}
                db.commit()

        print("Seeding complete!")
    except Exception as e:
        print(f"Error seeding DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
