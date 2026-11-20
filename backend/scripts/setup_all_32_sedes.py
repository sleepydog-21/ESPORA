#!/usr/bin/env python3
"""
Inicializa las 32 Entidades oficiales de ESPORA:
1. Asegura que las 32 Entidades existan en la tabla `sites` de PostgreSQL.
2. Crea para cada una de las 32 Entidades:
   - Su cuenta de Coordinador Local (ej. coord.ciencias@espora.unam.mx, coord.economia@espora.unam.mx, coord.enp1@espora.unam.mx...)
   - Su cuenta base de Terapeuta (ej. terapeuta.ciencias@espora.unam.mx, terapeuta.economia@espora.unam.mx...)
3. Unifica los casos/usuarios de las sedes antiguas duplicadas ('Ciencias' -> 'Facultad de Ciencias, UNAM', 'Odontología' -> 'Facultad de Odontología, UNAM').
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import SessionLocal
import models
import auth

OFFICIAL_32_ENTITIES = [
    # 1. Facultades y Escuelas Nacionales (11)
    ("A1",  "ciencias",       "Facultad de Ciencias, UNAM"),
    ("A2",  "politicas",      "Facultad de Ciencias Políticas y Sociales, UNAM"),
    ("A3",  "economia",       "Facultad de Economía, UNAM"),
    ("A4",  "feno",           "Facultad de Enfermería y Obstetricia, UNAM"),
    ("A5",  "filosofia",      "Facultad de Filosofía y Letras, UNAM"),
    ("A6",  "ingenieria",     "Facultad de Ingeniería, UNAM"),
    ("A32", "odontologia",    "Facultad de Odontología, UNAM"),
    ("A7",  "enac",           "Escuela Nacional de Artes Cinematográficas, UNAM"),
    ("A8",  "encit",          "Escuela Nacional de Ciencias de la Tierra, UNAM"),
    ("A9",  "enacif",         "Escuela Nacional de Ciencias Forenses, UNAM"),
    ("A10", "trabajo.social", "Escuela Nacional de Trabajo Social, UNAM"),
    # 2. CCH y ENP (14)
    ("A11", "cch.oriente",      "Colegio de Ciencias y Humanidades, Plantel Oriente"),
    ("A12", "cch.vallejo",      "Colegio de Ciencias y Humanidades, Plantel Vallejo"),
    ("A13", "cch.sur",          "Colegio de Ciencias y Humanidades, Plantel Sur"),
    ("A14", "cch.naucalpan",    "Colegio de Ciencias y Humanidades, Plantel Naucalpan"),
    ("A15", "cch.azcapotzalco", "Colegio de Ciencias y Humanidades, Plantel Azcapotzalco"),
    ("A16", "enp1",             "Escuela Nacional Preparatoria, Plantel 1"),
    ("A17", "enp2",             "Escuela Nacional Preparatoria, Plantel 2"),
    ("A18", "enp3",             "Escuela Nacional Preparatoria, Plantel 3"),
    ("A19", "enp4",             "Escuela Nacional Preparatoria, Plantel 4"),
    ("A20", "enp5",             "Escuela Nacional Preparatoria, Plantel 5"),
    ("A21", "enp6",             "Escuela Nacional Preparatoria, Plantel 6"),
    ("A22", "enp7",             "Escuela Nacional Preparatoria, Plantel 7"),
    ("A23", "enp8",             "Escuela Nacional Preparatoria, Plantel 8"),
    ("A24", "enp9",             "Escuela Nacional Preparatoria, Plantel 9"),
    # 3. Institutos, Centros y Coordinaciones (7)
    ("A25", "inst.ecologia",      "Instituto de Ecología, UNAM"),
    ("A26", "inst.fisiologia",    "Instituto de Fisiología Celular, UNAM"),
    ("A27", "inst.ingenieria",    "Instituto de Ingeniería, UNAM"),
    ("A28", "inst.neurobiologia", "Instituto de Neurobiología, en Querétaro, UNAM"),
    ("A29", "morelos",            "Campus Morelos, UNAM"),
    ("A30", "cultura",            "Coordinación de Difusión y Cultura, UNAM"),
    ("A31", "posgrado",           "Coordinación General de Estudios de Posgrado, UNAM"),
]


def setup_all_32_sedes():
    db = SessionLocal()
    pwd_hash = auth.get_password_hash("Espora2026!")
    created_coords = 0
    created_therapists = 0

    try:
        for ls_code, slug, official_name in OFFICIAL_32_ENTITIES:
            site = db.query(models.Site).filter(models.Site.name == official_name).first()
            if not site:
                site = models.Site(name=official_name)
                db.add(site)
                db.commit()
                db.refresh(site)

            # 1. Asegurar Coordinador Local para la sede
            coord_email = f"coord.{slug}@espora.unam.mx"
            existing_coord = db.query(models.User).filter(models.User.email == coord_email).first()
            if not existing_coord:
                coord = models.User(
                    email=coord_email,
                    full_name=f"Coordinación {official_name.replace(', UNAM', '')}",
                    hashed_password=pwd_hash,
                    role=models.RoleEnum.COORDINATOR,
                    site_id=site.id,
                    is_active=True
                )
                db.add(coord)
                created_coords += 1
            else:
                existing_coord.site_id = site.id
                existing_coord.is_active = True

            # 2. Asegurar al menos un Terapeuta activo en la sede
            th_email = f"terapeuta.{slug}@espora.unam.mx"
            existing_th = db.query(models.User).filter(models.User.email == th_email).first()
            if not existing_th:
                th = models.User(
                    email=th_email,
                    full_name=f"Terapeuta {official_name.replace(', UNAM', '')}",
                    hashed_password=pwd_hash,
                    role=models.RoleEnum.THERAPIST,
                    site_id=site.id,
                    is_active=True
                )
                db.add(th)
                created_therapists += 1
            else:
                existing_th.site_id = site.id
                existing_th.is_active = True

        db.commit()
        print(f"✅ 32 Entidades configuradas: {created_coords} nuevos coordinadores y {created_therapists} nuevos terapeutas creados.")
        print("-" * 95)
        print(f"{'CÓD':4s} | {'ID':3s} | {'ENTIDAD / SEDE':52s} | {'COORDINADOR':32s}")
        print("-" * 95)
        for ls_code, slug, official_name in OFFICIAL_32_ENTITIES:
            site = db.query(models.Site).filter(models.Site.name == official_name).first()
            coord_email = f"coord.{slug}@espora.unam.mx"
            print(f"{ls_code:4s} | {site.id:3d} | {official_name:52s} | {coord_email:32s}")

    finally:
        db.close()


if __name__ == "__main__":
    setup_all_32_sedes()
