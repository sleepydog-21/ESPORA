from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

import models
from database import get_db

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)

class LimesurveyPayload(BaseModel):
    full_name: str
    student_account: str
    email: str
    phone: Optional[str] = None
    faculty_site_name: str
    career: Optional[str] = None
    gender: Optional[str] = "No especificado"

@router.post("/limesurvey")
def receive_limesurvey_submission(
    payload: LimesurveyPayload,
    db: Session = Depends(get_db)
):
    try:
        # Find the faculty site
        site = db.query(models.Site).filter(models.Site.name.ilike(f"%{payload.faculty_site_name}%")).first()
        if not site:
            # Create raw site or put in a holding bin. For now, create unmapped site.
            site = models.Site(name=payload.faculty_site_name)
            db.add(site)
            db.commit()
            db.refresh(site)
            
        # Check if participant already exists via account number
        participant = db.query(models.Participant).filter(models.Participant.student_account == payload.student_account).first()
        
        if not participant:
            participant = models.Participant(
                full_name=payload.full_name,
                student_account=payload.student_account,
                email=payload.email,
                phone=payload.phone,
                gender=payload.gender,
                faculty=payload.faculty_site_name,
                career=payload.career,
                site_id=site.id
            )
            db.add(participant)
            db.commit()
            db.refresh(participant)
            
        # Create Case in Waiting List
        new_case = models.Case(
            participant_id=participant.id,
            site_id=site.id,
            status=models.CaseStatusEnum.WAITING,
            intake_source="limesurvey"
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        
        return {"status": "success", "case_id": new_case.id, "participant_id": participant.id}
        
    except Exception as e:
        print("Webhook Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
