from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/cases",
    tags=["cases"],
)

@router.get("/", response_model=List[schemas.CaseResponse])
def get_cases(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    query = db.query(models.Case)
    
    if current_user.role == models.RoleEnum.COORDINATOR:
        query = query.filter(models.Case.site_id == current_user.site_id)
    elif current_user.role == models.RoleEnum.THERAPIST:
        query = query.filter(models.Case.therapist_id == current_user.id)
        
    return query.offset(skip).limit(limit).all()

@router.post("/manual", response_model=schemas.CaseResponse)
def create_manual_case(
    participant_data: schemas.ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    # Ensure coordinators only create patients for their site
    if current_user.role == models.RoleEnum.COORDINATOR:
        participant_data.site_id = current_user.site_id

    # Create participant
    db_participant = models.Participant(**participant_data.dict())
    db.add(db_participant)
    db.commit()
    db.refresh(db_participant)

    # Create case
    db_case = models.Case(
        participant_id=db_participant.id,
        site_id=participant_data.site_id,
        status=models.CaseStatusEnum.WAITING,
        intake_source="manual"
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    return db_case

@router.post("/bulk", response_model=Dict[str, Any])
def create_manual_cases_bulk(
    participants_data: List[schemas.ParticipantCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    success_count = 0
    errors = []
    
    for i, p_data in enumerate(participants_data):
        try:
            if current_user.role == models.RoleEnum.COORDINATOR:
                p_data.site_id = current_user.site_id

            # Create participant
            db_participant = models.Participant(**p_data.dict())
            db.add(db_participant)
            db.flush() # flush to get participant id without committing full transaction yet

            # Create case
            db_case = models.Case(
                participant_id=db_participant.id,
                site_id=p_data.site_id,
                status=models.CaseStatusEnum.WAITING,
                intake_source="manual_bulk"
            )
            db.add(db_case)
            success_count += 1
        except Exception as e:
            errors.append(f"Row {i+1}: Error creando consultante {p_data.full_name}. Detalles: {str(e)}")
            db.rollback()
            # If one fails we continue with the rest, but must ensure session gets clean state if needed, though rollback handles it for the failed item
            
    db.commit()
    return {"success_count": success_count, "errors": errors}

@router.put("/{case_id}", response_model=schemas.CaseResponse)
def update_case(
    case_id: int,
    case_update: schemas.CaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    db_case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if current_user.role == models.RoleEnum.COORDINATOR and db_case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to update cases for this site")
        
    update_data = case_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_case, key, value)
        
    db.commit()
    db.refresh(db_case)
    return db_case

@router.put("/{case_id}/participant", response_model=schemas.ParticipantResponse)
def update_participant(
    case_id: int,
    participant_update: schemas.ParticipantUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    db_case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not db_case or not db_case.participant:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    if current_user.role == models.RoleEnum.COORDINATOR and db_case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to update participant for this site")
        
    db_participant = db_case.participant
    update_data = participant_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_participant, key, value)
        
    db.commit()
    db.refresh(db_participant)
    return db_participant

@router.post("/{case_id}/sessions", response_model=schemas.SessionResponse)
def create_session(
    case_id: int,
    session: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.THERAPIST]))
):
    db_case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if current_user.role == models.RoleEnum.THERAPIST and db_case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add sessions for this case")
        
    db_session = models.Session(**session.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Automatically send email on first scheduled session
    if db_case.status == models.CaseStatusEnum.ASSIGNED:
        db_case.status = models.CaseStatusEnum.ACTIVE
        db.commit()
        db.refresh(db_case)

        # Send email
        import smtplib
        from email.message import EmailMessage
        from config import settings
        
        participant_email = db_case.participant.email
        msg = EmailMessage()
        msg.set_content(
            f"Hola {db_case.participant.full_name},\n\n"
            f"Tu terapeuta ha sido asignado y tienes una cita programada para el {session.session_date.strftime('%d/%m/%Y a las %H:%M')}.\n\n"
            f"Modalidad: {session.modality.value if session.modality else 'Por definir'}\n\n"
            f"Saludos,\nPrograma ESPORA"
        )
        msg['Subject'] = 'Confirmación de cita - Programa ESPORA'
        msg['From'] = settings.mail_sender
        msg['To'] = participant_email

        try:
            with smtplib.SMTP(settings.mail_server, settings.mail_port) as server:
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")

    return db_session

@router.get("/{case_id}/process-data", response_model=schemas.CaseProcessDataResponse)
def get_case_process_data(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Check permissions
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case's data")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to access cases outside your site")
        
    process_data = db.query(models.CaseProcessData).filter(models.CaseProcessData.case_id == case_id).first()
    
    # Calculate auto-filled values from sessions & participant
    from datetime import datetime
    sessions = sorted(case.sessions, key=lambda s: s.session_date)
    
    completed_count = sum(1 for s in sessions if s.status == "completed")
    cancelled_count = sum(1 for s in sessions if s.status == "cancelled")
    
    first_date = sessions[0].session_date if sessions else None
    last_date = None
    if case.status == models.CaseStatusEnum.CLOSED or case.closed_at:
        last_date = case.closed_at or (sessions[-1].session_date if sessions else None)
        
    def get_sem(dt):
        if not dt:
            return None
        year = dt.year
        month = dt.month
        if 1 <= month <= 6:
            return f"{year}-2"
        else:
            return f"{year}-1"
            
    sem_ini = get_sem(first_date)
    sem_fin = get_sem(last_date)
    
    now = datetime.now()
    current_sem = get_sem(now)
    prev_year = now.year
    if now.month <= 6:
        prev_sem = f"{prev_year - 1}-1"
    else:
        prev_sem = f"{prev_year}-2"
        
    horas_act = 0
    horas_ant = 0
    for s in sessions:
        s_sem = get_sem(s.session_date)
        if s_sem == current_sem:
            horas_act += 1
        elif s_sem == prev_sem:
            horas_ant += 1
            
    sex = case.participant.gender if case.participant else None
    
    if not process_data:
        # First time creation, populate everything
        process_data = models.CaseProcessData(
            case_id=case_id,
            fecha_inicio=first_date,
            semestre_inicio=sem_ini,
            sexo=sex,
            sesiones_totales=completed_count,
            inasistencias=cancelled_count,
            horas_clinicas_actual=horas_act,
            horas_clinicas_anterior=horas_ant,
            fecha_finalizacion=last_date,
            semestre_finalizacion=sem_fin
        )
        db.add(process_data)
        db.commit()
        db.refresh(process_data)
    else:
        # Update dynamically calculated values only if they are not manually modified
        # If the values are 0 or Null in DB, we can auto-fill them
        updated = False
        if process_data.sesiones_totales is None or process_data.sesiones_totales == 0:
            process_data.sesiones_totales = completed_count
            updated = True
        if process_data.inasistencias is None or process_data.inasistencias == 0:
            process_data.inasistencias = cancelled_count
            updated = True
        if process_data.horas_clinicas_actual is None or process_data.horas_clinicas_actual == 0:
            process_data.horas_clinicas_actual = horas_act
            updated = True
        if process_data.horas_clinicas_anterior is None or process_data.horas_clinicas_anterior == 0:
            process_data.horas_clinicas_anterior = horas_ant
            updated = True
        if not process_data.fecha_inicio and first_date:
            process_data.fecha_inicio = first_date
            process_data.semestre_inicio = sem_ini
            updated = True
        if not process_data.fecha_finalizacion and last_date:
            process_data.fecha_finalizacion = last_date
            process_data.semestre_finalizacion = sem_fin
            updated = True
        if not process_data.sexo and sex:
            process_data.sexo = sex
            updated = True
            
        if updated:
            db.commit()
            db.refresh(process_data)
            
    return process_data

@router.put("/{case_id}/process-data", response_model=schemas.CaseProcessDataResponse)
def update_case_process_data(
    case_id: int,
    data_in: schemas.CaseProcessDataUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Check permissions
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this case's data")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify cases outside your site")
        
    process_data = db.query(models.CaseProcessData).filter(models.CaseProcessData.case_id == case_id).first()
    if not process_data:
        process_data = models.CaseProcessData(case_id=case_id)
        db.add(process_data)
        db.flush()
        
    update_dict = data_in.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(process_data, key, value)
        
    db.commit()
    db.refresh(process_data)
    return process_data

@router.post("/{case_id}/send-email")
def send_case_email(
    case_id: int,
    email_req: schemas.CaseSendEmailRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Check permissions
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes autorización para enviar correos en este caso")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="No tienes autorización para operar en sedes distintas a la tuya")

    target_email = email_req.recipient_email or (case.participant.email if case.participant else None)
    if not target_email:
        raise HTTPException(status_code=400, detail="El consultante no tiene un correo electrónico registrado")

    import smtplib
    from email.message import EmailMessage
    from config import settings

    msg = EmailMessage()
    msg.set_content(email_req.body)
    msg['Subject'] = email_req.subject
    msg['From'] = current_user.email or settings.mail_sender
    msg['To'] = target_email

    try:
        with smtplib.SMTP(settings.mail_server, settings.mail_port, timeout=10) as server:
            if settings.mail_use_tls:
                server.starttls()
            if settings.mail_username and settings.mail_password:
                server.login(settings.mail_username, settings.mail_password)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar el correo a través del servidor SMTP: {str(e)}")

    return {
        "status": "success",
        "message": f"Correo enviado exitosamente a {target_email}",
        "recipient": target_email
    }


@router.post("/{case_id}/refer_from_api", response_model=schemas.CaseResponse)
def refer_from_api(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.API_THERAPIST, models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if current_user.role == models.RoleEnum.API_THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refer this case")
        
    # Unassign therapist and return to waitlist
    case.status = models.CaseStatusEnum.WAITING
    case.therapist_id = None
    
    # Mark in process data
    process_data = db.query(models.CaseProcessData).filter(models.CaseProcessData.case_id == case_id).first()
    if not process_data:
        process_data = models.CaseProcessData(case_id=case_id, tuvo_intervencion_api=True)
        db.add(process_data)
    else:
        process_data.tuvo_intervencion_api = True
        
    db.commit()
    db.refresh(case)
    
    return case

