from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

import models
from database import get_db

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)

@router.post("/limesurvey")
def receive_limesurvey_submission(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # 1. Extraer campos estándar obligatorios para Participante y Caso
        full_name = payload.pop("full_name", None)
        student_account = payload.pop("student_account", None)
        email = payload.pop("email", None)
        phone = payload.pop("phone", None)
        faculty_site_name = payload.pop("faculty_site_name", None)
        career = payload.pop("career", None)
        gender = payload.pop("gender", "No especificado")
        
        if not full_name or not student_account or not faculty_site_name:
            raise HTTPException(status_code=422, detail="Missing required fields: full_name, student_account, or faculty_site_name")

        # Buscar o crear la facultad/sede
        site = db.query(models.Site).filter(models.Site.name.ilike(f"%{faculty_site_name}%")).first()
        if not site:
            site = models.Site(name=faculty_site_name)
            db.add(site)
            db.commit()
            db.refresh(site)
            
        # Verificar si el participante ya existe (por matrícula)
        participant = db.query(models.Participant).filter(models.Participant.student_account == student_account).first()
        
        if not participant:
            participant = models.Participant(
                full_name=full_name,
                student_account=student_account,
                email=email,
                phone=phone,
                gender=gender,
                faculty=faculty_site_name,
                career=career,
                site_id=site.id
            )
            db.add(participant)
            db.commit()
            db.refresh(participant)
            
            # Generar folio anónimo: 2 dígitos de sede + 5 dígitos del ID del participante
            participant.anonymous_folio = f"{site.id:02d}{participant.id:05d}"
            db.commit()
            db.refresh(participant)
            
        # Crear Caso en estado WAITING (Lista de Espera)
        new_case = models.Case(
            participant_id=participant.id,
            site_id=site.id,
            status=models.CaseStatusEnum.WAITING,
            intake_source="limesurvey"
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        
        # 2. Integración con Formularios Dinámicos
        # Buscar o crear la plantilla autogenerada para LimeSurvey
        template_name = "Ficha de Ingreso (LimeSurvey)"
        template = db.query(models.FormTemplate).filter(models.FormTemplate.name == template_name).first()
        if not template:
            template = models.FormTemplate(
                name=template_name, 
                description="Plantilla autogenerada desde Webhook de LimeSurvey"
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            
        # Crear la Sumisión conectada al Participante y al Caso
        submission = models.FormSubmission(
            form_template_id=template.id,
            participant_id=participant.id,
            case_id=new_case.id
        )
        db.add(submission)
        db.flush()
        
        # Guardar las respuestas dinámicas de las llaves sobrantes del JSON
        for key, value in payload.items():
            if value is None or value == "":
                continue
                
            # Verificar si el campo ya existe en la plantilla
            field = db.query(models.FormField).filter(
                models.FormField.form_template_id == template.id,
                models.FormField.name == key
            ).first()
            
            # Si el campo es nuevo, crearlo dinámicamente
            if not field:
                field = models.FormField(
                    form_template_id=template.id,
                    name=key,
                    label=key.replace('_', ' ').capitalize(),
                    field_type=models.FieldTypeEnum.STRING
                )
                db.add(field)
                db.flush()
                
            # Guardar el valor de la respuesta
            field_val = models.FormFieldValue(
                form_submission_id=submission.id,
                form_field_id=field.id,
                value_text=str(value)
            )
            db.add(field_val)
            
        db.commit()
        
        return {
            "status": "success", 
            "case_id": new_case.id, 
            "participant_id": participant.id, 
            "submission_id": submission.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print("Webhook Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
