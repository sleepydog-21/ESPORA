from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timedelta
from typing import List, Optional

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)

@router.get("/therapist", response_model=List[schemas.SessionResponse])
def get_therapist_sessions(
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.THERAPIST, models.RoleEnum.COORDINATOR]))
):
    # Fetch all sessions belonging to cases assigned to this therapist
    sessions = db.query(models.Session).join(models.Case).filter(
        models.Case.therapist_id == current_user.id
    ).all()
    return sessions

@router.post("/biweekly", response_model=List[schemas.SessionResponse])
def generate_biweekly(
    payload: schemas.SessionBiweeklyCreate,
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.THERAPIST]))
):
    # verify case ownership
    case = db.query(models.Case).filter(models.Case.id == payload.case_id, models.Case.therapist_id == current_user.id).first()
    if not case:
        raise HTTPException(status_code=403, detail="No autorizado para este caso")
        
    created_sessions = []
    # Make sure start_date is timezone aware if frontend sends UTC
    current_date = payload.start_date
    sessions_to_create = payload.num_sessions if payload.num_sessions else 14
    
    for i in range(sessions_to_create):
        new_session = models.Session(
            case_id=case.id,
            session_date=current_date,
            status="scheduled",
            therapist_notes=None
        )
        db.add(new_session)
        created_sessions.append(new_session)
        current_date += timedelta(days=14)
        
    db.commit()
    for s in created_sessions:
        db.refresh(s)
    return created_sessions

@router.put("/{session_id}", response_model=schemas.SessionResponse)
def update_session(
    session_id: int,
    session_in: schemas.SessionBase,
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.THERAPIST, models.RoleEnum.COORDINATOR, models.RoleEnum.ADMIN]))
):
    session_db = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_db:
        raise HTTPException(status_code=404)
        
    # check ownership
    if current_user.role == models.RoleEnum.THERAPIST and session_db.case_ref.therapist_id != current_user.id:
        raise HTTPException(status_code=403)
        
    session_db.session_date = session_in.session_date
    if session_in.therapist_notes is not None:
        session_db.therapist_notes = session_in.therapist_notes
    if session_in.status is not None:
        session_db.status = session_in.status
        
    db.commit()
    db.refresh(session_db)
    return session_db

@router.post("/", response_model=schemas.SessionResponse)
def create_single_session(
    session_in: schemas.SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.THERAPIST]))
):
    case = db.query(models.Case).filter(models.Case.id == session_in.case_id, models.Case.therapist_id == current_user.id).first()
    if not case:
        raise HTTPException(status_code=403)
        
    new_session = models.Session(
        case_id=case.id,
        session_date=session_in.session_date,
        status=session_in.status or "scheduled",
        therapist_notes=session_in.therapist_notes
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session
