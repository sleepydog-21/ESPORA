from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List

import auth
import models
from database import get_db
from services.limesurvey_service import limesurvey_service

router = APIRouter(
    prefix="/limesurvey",
    tags=["limesurvey"],
)

@router.get("/status")
def get_limesurvey_status(current_user: models.User = Depends(auth.get_current_active_user)):
    """
    Verifica si el microservicio limesurvey-connector en la infraestructura del C3 responde.
    """
    return limesurvey_service.check_health()

@router.get("/surveys")
def list_limesurvey_surveys(
    refresh: bool = Query(False, description="Ignorar caché y consultar LimeSurvey directamente"),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Lista las encuestas disponibles para el usuario configurado en LimeSurvey.
    """
    if current_user.role not in [models.RoleEnum.COORDINATOR, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]:
        raise HTTPException(status_code=403, detail="No tienes permisos para consultar encuestas.")
    try:
        return limesurvey_service.list_surveys(refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync")
def sync_limesurvey_survey(
    survey_id: Optional[str] = Query(None, description="ID de la encuesta a sincronizar"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Inicia la sincronización activa de respuestas traducidas desde LimeSurvey hacia la Lista de Espera de ESPORA.
    Solo coordinadores y administradores pueden disparar esta sincronización.
    """
    if current_user.role not in [
        models.RoleEnum.COORDINATOR,
        models.RoleEnum.GENERAL_COORDINATOR,
        models.RoleEnum.ADMIN,
        models.RoleEnum.THERAPIST,
        models.RoleEnum.API_THERAPIST,
    ]:
        raise HTTPException(status_code=403, detail="No tienes permisos para sincronizar encuestas.")

    try:
        report = limesurvey_service.sync_responses(survey_id=survey_id, db=db)
        return {
            "status": "success",
            "message": f"Sincronización completada. {report['new_cases']} nuevos casos en lista de espera.",
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo en la sincronización con LimeSurvey: {str(e)}")

@router.post("/ingest-batch")
def ingest_translated_batch(
    payload: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Permite importar directamente un lote de respuestas ya traducidas desde un archivo o exportación externa.
    """
    report = {
        "total_received": len(payload),
        "new_cases": 0,
        "updated_cases": 0,
        "high_risk_alerts": 0,
        "details": []
    }

    for item in payload:
        try:
            res = limesurvey_service.ingest_single_response(item, db)
            if res["created_case"]:
                report["new_cases"] += 1
            else:
                report["updated_cases"] += 1
            if res["is_high_risk"]:
                report["high_risk_alerts"] += 1
            report["details"].append(res)
        except Exception as e:
            report["details"].append({"error": str(e), "raw": item})

    return report
