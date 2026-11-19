#!/usr/bin/env python3
"""
Script de verificación de conexión y sincronización con LimeSurvey (Servicio C3).
Uso:
    python backend/scripts/test_limesurvey_connection.py
"""

import sys
import os

# Asegurar path al backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.limesurvey_service import limesurvey_service
from database import SessionLocal

def main():
    print("=" * 60)
    print("🌿 ESPORA - Diagnóstico de Conexión con LimeSurvey")
    print("=" * 60)
    print(f"URL del Servicio C3 : {limesurvey_service.api_url}")
    print(f"Host RPC LimeSurvey : {limesurvey_service.rpc_url}")
    print(f"Usuario LimeSurvey  : {limesurvey_service.username}")
    print(f"API Key configurada : {'Sí (***)' if limesurvey_service.api_key else 'No configurada aún'}")
    print(f"Password configurado: {'Sí (***)' if limesurvey_service.password else 'Falta LIMESURVEY_PASSWORD'}")
    print(f"ID Encuesta default : {limesurvey_service.default_sid or 'No configurado'}")
    print("-" * 60)

    print("1. Probando conectividad y X-Api-Key con https://lsapi.c3.unam.mx...")
    health = limesurvey_service.check_health()
    if health.get("connected") and health.get("api_key_valid"):
        print("✅ Microservicio CONECTADO y X-Api-Key VÁLIDA.")
        print(f"   Detalles: {health}")
    elif health.get("connected"):
        print("⚠️  Microservicio conectado pero X-Api-Key rechazada.")
        print(f"   Detalles: {health}")
    else:
        print("⚠️  Microservicio NO alcanzable en la red actual.")
        print(f"   Mensaje: {health.get('error') or health}")

    if limesurvey_service.password:
        print("-" * 60)
        print("1b. Abriendo sesión en LimeSurvey (POST /v1/limesurvey/sessions)...")
        try:
            session_info = limesurvey_service.open_session()
            print(f"✅ Sesión abierta exitosamente. Expira en: {session_info.get('expiresAt')}")
            surveys = limesurvey_service.list_surveys()
            print(f"✅ Encuestas visibles para '{limesurvey_service.username}': {surveys}")
        except Exception as e:
            print(f"❌ Error al abrir sesión o listar encuestas: {e}")

    print("-" * 60)
    print("2. Probando ingesta de prueba en base de datos local...")
    db = SessionLocal()
    sample_response = {
        "full_name": "Estudiante Prueba Conector",
        "student_account": "423099999",
        "email": "prueba.conector@alumno.unam.mx",
        "phone": "5500001122",
        "faculty_site_name": "Facultad de Psicología",
        "career": "Psicología",
        "gender": "Femenino",
        "limesurvey_summary": "El estudiante refiere episodios recurrentes de ansiedad ante exámenes y problemas de sueño.",
        "pregunta_escala_depresion": "Leve",
        "motivo_consulta": "Ansiedad y estrés escolar"
    }
    
    try:
        result = limesurvey_service.ingest_single_response(sample_response, db)
        print("✅ Ingesta de expediente de prueba EXITOSA:")
        print(f"   Caso ID: {result['case_id']}, Folio: {result['folio']}, Riesgo: {result['risk_words_found']}")
    except Exception as e:
        print(f"❌ Error en ingesta local: {e}")
    finally:
        db.close()

    print("=" * 60)
    print("Diagnóstico finalizado.")

if __name__ == "__main__":
    main()
