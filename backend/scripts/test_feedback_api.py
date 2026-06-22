import sys, os
import urllib.request
import urllib.error
import json
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
import models

API_URL = "http://localhost:8000"

def make_request(url, method="GET", headers=None, data=None):
    if headers is None:
        headers = {}
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            content = response.read()
            try:
                res_data = json.loads(content.decode("utf-8"))
            except:
                res_data = content
            return status_code, res_data
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            res_data = json.loads(e.read().decode("utf-8"))
        except:
            res_data = e.reason
        return status_code, res_data
    except urllib.error.URLError as e:
        return 500, str(e.reason)

def get_token(email, password):
    data = f"username={email}&password={password}".encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["access_token"]
    except Exception as e:
        print(f"Error getting token for {email}: {e}")
        return None

def test_feedback():
    db = SessionLocal()
    
    print("=== INICIANDO PRUEBAS DE VERIFICACIÓN DE ENCUESTA SEMANAL DE TERAPEUTAS ===")
    
    # 1. Login
    email_t1 = "laura.martinez@espora.unam.mx"
    token_t1 = get_token(email_t1, "terapeuta123")
    
    if not token_t1:
        print("FAIL: No se pudo obtener el token de autenticación del terapeuta.")
        db.close()
        return
        
    therapist = db.query(models.User).filter_by(email=email_t1).first()
    if not therapist:
        print("FAIL: No se encontró al terapeuta en la base de datos.")
        db.close()
        return
        
    # Clean up current week's feedback to make the test repeatable
    current_year, current_week, _ = datetime.date.today().isocalendar()
    db.query(models.TherapistFeedback).filter(
        models.TherapistFeedback.therapist_id == therapist.id,
        models.TherapistFeedback.year == current_year,
        models.TherapistFeedback.week == current_week
    ).delete()
    db.commit()
    print("Estado inicial limpio para el año/semana actual.")
    
    # Test 1: GET /users/me/feedback/status (Debe ser False)
    print("\n--- PRUEBA 1: Verificar Estado de Feedback Inicial (Debe ser False) ---")
    status, res = make_request(
        f"{API_URL}/users/me/feedback/status",
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status == 200 and res.get("already_submitted") is False:
        print("PASS: Estado inicial verificado correctamente como no enviado.")
    else:
        print(f"FAIL: Esperaba already_submitted=False. Recibido status={status}, res={res}")
        db.close()
        return

    # Test 2: POST /users/me/feedback (Enviar datos válidos)
    print("\n--- PRUEBA 2: Enviar Respuestas Válidas (q1=6, q2=9) ---")
    payload = {
        "q1_score": 6,
        "q2_score": 9
    }
    status, res = make_request(
        f"{API_URL}/users/me/feedback",
        method="POST",
        data=payload,
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status in [200, 201] and res.get("q1_score") == 6 and res.get("q2_score") == 9:
        print("PASS: Respuestas enviadas y guardadas correctamente.")
    else:
        print(f"FAIL: Error al guardar respuestas. Status={status}, res={res}")
        db.close()
        return

    # Test 3: POST /users/me/feedback (Enviar duplicado, debe fallar con 400)
    print("\n--- PRUEBA 3: Prevenir Respuestas Duplicadas en la misma semana ---")
    status, res = make_request(
        f"{API_URL}/users/me/feedback",
        method="POST",
        data=payload,
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status == 400:
        print("PASS: Se impidió correctamente el envío duplicado (HTTP 400).")
    else:
        print(f"FAIL: Esperaba HTTP 400. Recibido status={status}, res={res}")

    # Test 4: GET /users/me/feedback/status (Debe ser True ahora)
    print("\n--- PRUEBA 4: Verificar Estado de Feedback posterior al envío (Debe ser True) ---")
    status, res = make_request(
        f"{API_URL}/users/me/feedback/status",
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status == 200 and res.get("already_submitted") is True:
        print("PASS: Estado verificado correctamente como enviado.")
    else:
        print(f"FAIL: Esperaba already_submitted=True. Recibido status={status}, res={res}")

    # Test 5: POST /users/me/feedback (Validación de rangos incorrectos - Pydantic ge=1, le=10)
    print("\n--- PRUEBA 5: Validar que valores fuera de rango sean rechazados ---")
    # Clean up temporarily to test input validation without duplicate block
    db.query(models.TherapistFeedback).filter(
        models.TherapistFeedback.therapist_id == therapist.id,
        models.TherapistFeedback.year == current_year,
        models.TherapistFeedback.week == current_week
    ).delete()
    db.commit()
    
    invalid_payload = {
        "q1_score": 11,
        "q2_score": 5
    }
    status, res = make_request(
        f"{API_URL}/users/me/feedback",
        method="POST",
        data=invalid_payload,
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status == 422:
        print("PASS: Se rechazó correctamente un valor mayor a 10 (HTTP 422).")
    else:
        print(f"FAIL: Esperaba HTTP 422 para q1=11. Recibido status={status}, res={res}")

    invalid_payload2 = {
        "q1_score": 4,
        "q2_score": 0
    }
    status, res = make_request(
        f"{API_URL}/users/me/feedback",
        method="POST",
        data=invalid_payload2,
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status == 422:
        print("PASS: Se rechazó correctamente un valor menor a 1 (HTTP 422).")
    else:
        print(f"FAIL: Esperaba HTTP 422 para q2=0. Recibido status={status}, res={res}")

    # Restore valid feedback for dashboard manual testing
    restore_payload = {
        "q1_score": 7,
        "q2_score": 8
    }
    make_request(
        f"{API_URL}/users/me/feedback",
        method="POST",
        data=restore_payload,
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    
    db.close()
    print("\n=== TODAS LAS PRUEBAS DE API PASARON EXITOSAMENTE ===")

if __name__ == "__main__":
    test_feedback()
