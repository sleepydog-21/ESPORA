from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/sites",
    tags=["sites"],
)

@router.post("/", response_model=schemas.SiteResponse)
def create_site(
    site: schemas.SiteCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN]))
):
    db_site = db.query(models.Site).filter(models.Site.name == site.name).first()
    if db_site:
        raise HTTPException(status_code=400, detail="Site already exists")
    
    db_site = models.Site(name=site.name)
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site

@router.get("/", response_model=List[schemas.SiteResponse])
def read_sites(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return db.query(models.Site).offset(skip).limit(limit).all()

from datetime import datetime, timedelta

@router.get("/{site_id}/therapist_stats")
def get_therapist_stats(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.COORDINATOR, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.ADMIN]))
):
    if current_user.role == models.RoleEnum.COORDINATOR and current_user.site_id != site_id:
        raise HTTPException(status_code=403, detail="Not permitted to view other sites.")
        
    therapists = db.query(models.User).filter(
        models.User.site_id == site_id, 
        models.User.role == models.RoleEnum.THERAPIST
    ).all()
    
    stats = []
    # Calculate current week workload
    start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    end_of_week = start_of_week + timedelta(days=7)
    
    for t in therapists:
        cases = db.query(models.Case).filter(models.Case.therapist_id == t.id).all()
        active_cases = [c for c in cases if c.status == models.CaseStatusEnum.ACTIVE]
        dropouts = len([c for c in cases if c.status == models.CaseStatusEnum.CANCELLED])
        
        men_count = 0
        women_count = 0
        for c in active_cases:
            g = c.participant.gender if c.participant and c.participant.gender else ""
            if g and g.lower() in ["masculino", "hombre", "m"]:
                men_count += 1
            elif g and g.lower() in ["femenino", "mujer", "f"]:
                women_count += 1
                
        # Hours this week
        weekly_sessions = db.query(models.Session).join(models.Case).filter(
            models.Case.therapist_id == t.id,
            models.Session.session_date >= start_of_week,
            models.Session.session_date < end_of_week
        ).count()
        
        stats.append({
            "therapist_id": t.id,
            "therapist_name": t.full_name,
            "active_cases": len(active_cases),
            "dropouts": dropouts,
            "men": men_count,
            "women": women_count,
            "weekly_hours": weekly_sessions # assuming 1 hr per session
        })
        
    return stats
