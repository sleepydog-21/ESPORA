import sys, os
import urllib.request
import urllib.error
import json
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
            # Try parsing json
            try:
                res_data = json.loads(content.decode("utf-8"))
            except:
                res_data = content
            return status_code, res_data, response.info()
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            res_data = json.loads(e.read().decode("utf-8"))
        except:
            res_data = e.reason
        return status_code, res_data, None
    except urllib.error.URLError as e:
        return 500, str(e.reason), None

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

def test_fixes():
    db = SessionLocal()
    
    print("=== INICIANDO PRUEBAS DE VERIFICACIÓN DE CORRECCIONES ===")
    
    # 1. Login
    token_admin = get_token("admin@espora.unam.mx", "admin123")
    token_t1 = get_token("laura.martinez@espora.unam.mx", "terapeuta123") # Sede 1
    token_t2 = get_token("diego.fernandez@espora.unam.mx", "terapeuta123") # Sede 2
    token_coord1 = get_token("coord@espora.unam.mx", "coord123") # Sede 1
    token_coord2 = get_token("coord2@espora.unam.mx", "coord123") # Sede 2
    
    if not all([token_admin, token_t1, token_t2, token_coord1, token_coord2]):
        print("FAIL: No se pudieron obtener todos los tokens de autenticación.")
        db.close()
        return
        
    # Test 1: GET /export/case/{case_id}
    print("\n--- PRUEBA 1: Exportar Historial Clínico de Caso con Sesiones (/export/case/{id}) ---")
    status, res, headers = make_request(
        f"{API_URL}/export/case/6",
        headers={"Authorization": f"Bearer {token_t1}"}
    )
    if status == 200:
        print("PASS: Exportación de historial de caso exitosa (200 OK).")
        print(f"  -> Tamaño del archivo recibido: {len(res)} bytes")
    else:
        print(f"FAIL: Error al exportar historial de caso. Status: {status}, Detalle: {res}")
        
    # Test 2: GET /globals/export/data
    print("\n--- PRUEBA 2: Exportar Datos de Investigación (/globals/export/data) ---")
    status, res, headers = make_request(
        f"{API_URL}/globals/export/data",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    if status == 200:
        print("PASS: Exportación de datos de investigación global exitosa (200 OK).")
        print(f"  -> Registros devueltos: {len(res)}")
    else:
        print(f"FAIL: Error al exportar datos de investigación. Status: {status}, Detalle: {res}")
        
    # Test 3: GET /globals/audit_logs
    print("\n--- PRUEBA 3: Visualización de Auditoría (/globals/audit_logs) ---")
    status, res, headers = make_request(
        f"{API_URL}/globals/audit_logs",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    if status == 200:
        print("PASS: Consulta de logs de auditoría exitosa (200 OK).")
        print(f"  -> Logs obtenidos: {len(res)}")
    else:
        print(f"FAIL: Error al consultar logs de auditoría. Status: {status}, Detalle: {res}")

    # Test 4: Aislamiento de Sedes en Citas (/appointments/)
    print("\n--- PRUEBA 4: Aislamiento de Citas por Sede (Multi-Sitio) ---")
    status1, res1, _ = make_request(f"{API_URL}/appointments/", headers={"Authorization": f"Bearer {token_coord1}"})
    status2, res2, _ = make_request(f"{API_URL}/appointments/", headers={"Authorization": f"Bearer {token_coord2}"})
    
    if status1 == 200 and status2 == 200:
        apts1 = res1
        apts2 = res2
        
        coord1_user = db.query(models.User).filter_by(email="coord@espora.unam.mx").first()
        coord2_user = db.query(models.User).filter_by(email="coord2@espora.unam.mx").first()
        
        cruzado_apt1 = any(db.query(models.User).filter_by(id=a["therapist_id"]).first().site_id != coord1_user.site_id for a in apts1)
        cruzado_apt2 = any(db.query(models.User).filter_by(id=a["therapist_id"]).first().site_id != coord2_user.site_id for a in apts2)
        
        if not cruzado_apt1 and not cruzado_apt2:
            print("PASS: Aislamiento de citas exitoso. Ningún coordinador ve citas de otras sedes.")
        else:
            print(f"FAIL: Filtración detectada! Cruzado Sede 1: {cruzado_apt1}, Cruzado Sede 2: {cruzado_apt2}")
    else:
        print(f"FAIL: Error al consultar citas. Sede 1: {status1}, Sede 2: {status2}")

    # Test 5: Restricción de Envío de Formulario fuera de sede (/fields/submissions)
    print("\n--- PRUEBA 5: Seguridad en Envío de Formulario fuera de Sede ---")
    coord1_user = db.query(models.User).filter_by(email="coord@espora.unam.mx").first()
    case_s2 = db.query(models.Case).filter(models.Case.site_id != coord1_user.site_id).first() # Sede diferente
    if case_s2:
        payload = {
            "form_template_id": 1,
            "case_id": case_s2.id,
            "fields": []
        }
        status, res, _ = make_request(
            f"{API_URL}/fields/submissions",
            method="POST",
            data=payload,
            headers={"Authorization": f"Bearer {token_coord1}"}
        )
        if status == 403:
            print("PASS: Se bloqueó correctamente el envío de formulario para un caso fuera de la sede del coordinador.")
        else:
            print(f"FAIL: El coordinador pudo registrar un formulario fuera de su sede. Código recibido: {status}, Detalle: {res}")
    else:
        print("SKIP: No se encontró caso de otra sede para la prueba.")

    db.close()

if __name__ == "__main__":
    test_fixes()
