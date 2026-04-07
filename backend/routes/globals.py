from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/globals",
    tags=["globals"],
)

@router.get("/metrics", response_model=Dict[str, Any])
def get_global_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]))
):
    # Cross-site aggregated data
    # 1. Cases by site
    site_stats = db.query(
        models.Site.name,
        models.Case.status,
        func.count(models.Case.id).label("count")
    ).join(models.Case, models.Site.id == models.Case.site_id).group_by(
        models.Site.name, models.Case.status
    ).all()

    # 2. Time-series: cases created (Monthly, by site and status)
    time_series = db.query(
        models.Site.name.label("site"),
        func.date_trunc('month', models.Case.created_at).label("month"),
        models.Case.status.label("status"),
        func.count(models.Case.id).label("count")
    ).join(models.Case, models.Site.id == models.Case.site_id).group_by(
        models.Site.name, func.date_trunc('month', models.Case.created_at), models.Case.status
    ).all()
    
    # 3. Active Notifications
    active_alerts = db.query(models.Notification).filter(
        models.Notification.is_read == False,
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).all()

    return {
        "site_stats": [{"site": row[0], "status": row[1], "count": row[2]} for row in site_stats],
        "time_series": [{"site": row[0], "month": str(row[1].date()) if row[1] else None, "status": row[2], "count": row[3]} for row in time_series],
        "active_alerts": [
            {"id": a.id, "message": a.message, "site_id": a.site_id, "created_at": a.created_at} 
            for a in active_alerts
        ]
    }

@router.get("/alerts", response_model=List[schemas.AlertSettingResponse])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]))
):
    return db.query(models.AlertSetting).all()

@router.post("/alerts", response_model=schemas.AlertSettingResponse)
def create_alert(
    alert_setting: schemas.AlertSettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]))
):
    db_alert = models.AlertSetting(**alert_setting.dict(), created_by_id=current_user.id)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.get("/export/data")
def export_research_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]))
):
    cases = db.query(models.Case).all()
    field_defs = {fd.id: fd.name for fd in db.query(models.FieldDefinition).all()}
    
    values_raw = db.query(models.FieldValue).all()
    values_map = {}
    for v in values_raw:
        if v.participant_id not in values_map:
            values_map[v.participant_id] = {}
        f_name = field_defs.get(v.field_definition_id)
        if f_name:
            values_map[v.participant_id][f_name] = v.value

    flat_data = []
    for c in cases:
        p = c.participant
        row = {
            "ID_Caso": c.id,
            "Estado": c.status,
            "Sede": c.site.name if c.site else "Global",
            "Fecha_Ingreso": str(c.created_at),
            "Cuenta_Alumno": p.student_account,
            "Facultad": p.faculty or "N/D",
            "Carrera": p.career or "N/D",
            "Terapeuta_Asignado": c.therapist.full_name if c.therapist else "Sin Asignar"
        }
        
        p_fields = values_map.get(p.id, {})
        row.update(p_fields)
        flat_data.append(row)

    return flat_data

@router.get("/audit_logs")
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]))
):
    logs = db.query(
        models.AuditLog, models.User, models.FieldValue, models.FieldDefinition, models.Participant
    ).outerjoin(models.User, models.AuditLog.user_id == models.User.id)\
     .outerjoin(models.FieldValue, models.AuditLog.record_id == models.FieldValue.id)\
     .outerjoin(models.FieldDefinition, models.FieldValue.field_definition_id == models.FieldDefinition.id)\
     .outerjoin(models.Participant, models.FieldValue.participant_id == models.Participant.id)\
     .filter(models.AuditLog.table_name == "field_values")\
     .order_by(models.AuditLog.timestamp.desc())\
     .limit(limit).all()

    result = []
    for log, user, f_val, f_def, part in logs:
        result.append({
            "id": log.id,
            "Fecha": log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/D",
            "Usuario": user.email if user else "Sistema",
            "Paciente": part.full_name if part else "Desconocido",
            "Campo": f_def.label if f_def else "Campo Desconocido",
            "Accion": log.action,
            "Valor Anterior": str(log.old_value.get("value", "") if log.old_value else ""),
            "Nuevo Valor": str(log.new_value.get("value", "") if log.new_value else "")
        })
    return result
