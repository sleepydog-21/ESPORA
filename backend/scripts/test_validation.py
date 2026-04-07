import sys, os
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
import models

API_URL = "http://localhost:8000"

def get_token(email, password):
    r = requests.post(f"{API_URL}/token", data={"username": email, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    return None

def test_permissions():
    db = SessionLocal()
    
    print("--- STARTING VALIDATION TESTS ---")
    
    # 1. Login
    token_t1 = get_token("laura.martinez@espora.unam.mx", "terapeuta123") # Odontologia
    token_t2 = get_token("diego.fernandez@espora.unam.mx", "terapeuta123") # Ciencias
    token_coord1 = get_token("coord@espora.unam.mx", "coord123") # Odontologia coord
    
    # Get patients for T1
    r = requests.get(f"{API_URL}/cases", headers={"Authorization": f"Bearer {token_t1}"})
    cases_t1 = r.json()
    if not cases_t1:
        print("FAIL: T1 has no cases")
        return
        
    case_t1_id = cases_t1[0]["id"]
    participant_t1_id = cases_t1[0]["participant_id"]
    
    # Get patients for T2
    r = requests.get(f"{API_URL}/cases", headers={"Authorization": f"Bearer {token_t2}"})
    cases_t2 = r.json()
    case_t2_id = cases_t2[0]["id"]
    
    print("\n--- TEST 1: Role Permissions ---")
    # T1 tries to edit T2's case
    payload = {"fields": {"motivo_consulta": "Hacked by T1"}}
    r_hack = requests.put(f"{API_URL}/fields/case/{case_t2_id}/values", json=payload, headers={"Authorization": f"Bearer {token_t1}"})
    if r_hack.status_code == 403:
         print("PASS: Therapist cannot edit another therapist's patient.")
    else:
         print(f"FAIL: Therapist edited another patient! Code: {r_hack.status_code}")
         
    # Coord1 (Odonto) tries to edit T2's case (Ciencias)
    r_hack2 = requests.put(f"{API_URL}/fields/case/{case_t2_id}/values", json=payload, headers={"Authorization": f"Bearer {token_coord1}"})
    if r_hack2.status_code == 403:
         print("PASS: Coordinator cannot edit case outside their site.")
    else:
         print(f"FAIL: Coordinator edited case outside their site! Code: {r_hack2.status_code}")

    print("\n--- TEST 2: Dynamic Fields Edit & 422 Debug ---")
    # T1 edits their own case
    payload_valid = {"fields": {"motivo_consulta": "Ansiedad severa test", "bdi_score": "22", "diagnostico_cie10": "F41.1"}}
    r_edit = requests.put(f"{API_URL}/fields/case/{case_t1_id}/values", json=payload_valid, headers={"Authorization": f"Bearer {token_t1}"})
    if r_edit.status_code == 200:
        print("PASS: T1 successfully edited their own case's dynamic fields.")
    else:
        print(f"FAIL: T1 could not edit case. Code: {r_edit.status_code}, Msg: {r_edit.text}")

    print("\n--- TEST 3: Audit Log Verification ---")
    # Verify the database explicitly to see if AuditLog trapped the modification
    logs = db.query(models.AuditLog).filter(models.AuditLog.record_id == participant_t1_id).all()
    if logs:
        print(f"PASS: Found {len(logs)} audit logs for this edits.")
        for log in logs[-3:]: # check last 3
            print(f"  -> Audit {log.id}: Action={log.action.value}, Field={log.new_value.get('field')}, Val={log.new_value.get('val')}, UserId={log.user_id}")
    else:
        print("FAIL: No audit logs found in the database. TRACEABILITY BROKEN.")
        
    db.close()

if __name__ == "__main__":
    test_permissions()
