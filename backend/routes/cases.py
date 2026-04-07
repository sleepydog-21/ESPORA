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
