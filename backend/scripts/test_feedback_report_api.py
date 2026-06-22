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

def test_feedback_report():
    print("=== INICIANDO PRUEBAS DE AUTORIZACIÓN Y FILTRADO DEL REPORTE DE FEEDBACK ===")
    
    # 1. Test Therapist authorization (should get 403 Forbidden)
    print("\n--- PRUEBA 1: Verificar que un terapeuta reciba HTTP 403 Forbidden ---")
    token_therapist = get_token("laura.martinez@espora.unam.mx", "terapeuta123")
    if not token_therapist:
        print("FAIL: No se pudo loguear al terapeuta.")
        return
        
    status, res = make_request(
        f"{API_URL}/users/feedback/report",
        headers={"Authorization": f"Bearer {token_therapist}"}
    )
    if status == 403:
        print("PASS: Terapeuta rechazado correctamente con HTTP 403.")
    else:
        print(f"FAIL: Se esperaba HTTP 403. Recibido status={status}, res={res}")
        
    # 2. Test Local Coordinator authorization and site isolation
    print("\n--- PRUEBA 2: Verificar que el coordinador local solo vea datos de su sede ---")
    db = SessionLocal()
    coord_user = db.query(models.User).filter_by(email="coord@espora.unam.mx").first()
    if not coord_user:
        print("FAIL: No se encontró al coordinador 1 en la base de datos.")
        db.close()
        return
    
    coord_site_id = coord_user.site_id
    print(f"Coordinador Local 1 pertenece a la Sede ID: {coord_site_id}")
    
    token_coord = get_token("coord@espora.unam.mx", "coord123")
    if not token_coord:
        print("FAIL: No se pudo loguear al coordinador.")
        db.close()
        return
        
    status, res = make_request(
        f"{API_URL}/users/feedback/report",
        headers={"Authorization": f"Bearer {token_coord}"}
    )
    
    if status == 200:
        print(f"PASS: Coordinador local accedió correctamente. Registros recibidos: {len(res)}")
        # Verify that all items in report belong to the coordinator's site
        all_match = True
        for report_item in res:
            if report_item.get("site_id") != coord_site_id:
                all_match = False
                print(f"FAIL: Encontrado registro de otra sede: {report_item}")
        if all_match:
            print("PASS: Aislamiento de sede verificado. Todos los registros corresponden a su sede.")
    else:
        print(f"FAIL: Se esperaba HTTP 200. Recibido status={status}, res={res}")

    # 3. Test General Coordinator authorization (should see all sites)
    print("\n--- PRUEBA 3: Verificar que el coordinador general vea registros sin restricción de sede ---")
    token_general = get_token("coord.general@espora.unam.mx", "admin123")
    if not token_general:
        # Fallback to admin if general coordinator not created
        print("Intentando loguear con Admin ya que General Coordinador no respondió...")
        token_general = get_token("admin@espora.unam.mx", "admin123")
        
    if not token_general:
        print("FAIL: No se pudo loguear al administrador/coordinador general.")
        db.close()
        return
        
    status, res = make_request(
        f"{API_URL}/users/feedback/report",
        headers={"Authorization": f"Bearer {token_general}"}
    )
    
    if status == 200:
        print(f"PASS: Coordinador general/Admin accedió correctamente. Registros recibidos: {len(res)}")
        # Check if there are different sites present (if we have seeds from multiple sites)
        site_ids = {item.get("site_id") for item in res}
        print(f"Sedes encontradas en el reporte global: {site_ids}")
    else:
        print(f"FAIL: Se esperaba HTTP 200. Recibido status={status}, res={res}")
        
    db.close()
    print("\n=== FINALIZACIÓN DE PRUEBAS ===")

if __name__ == "__main__":
    test_feedback_report()
