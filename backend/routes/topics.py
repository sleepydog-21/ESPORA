from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_
from typing import List

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/topics",
    tags=["topics"],
)

@router.get("/", response_model=List[schemas.TopicResponse])
def get_topics(
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Topics are either global (site_id is null) or belong to the user's site
    query = db.query(models.Topic).filter(models.Topic.is_active == True)
    
    if current_user.site_id:
        query = query.filter(or_(models.Topic.site_id == None, models.Topic.site_id == current_user.site_id))
    else:
        # If user has no site (e.g., admin or general coord), maybe show all or just global
        # Let's show all global for general coord, plus they can probably see all if they want, but let's stick to global
        if current_user.role == models.RoleEnum.GENERAL_COORDINATOR:
            pass # allow seeing all topics
        else:
            query = query.filter(models.Topic.site_id == None)
            
    return query.all()

@router.post("/", response_model=schemas.TopicResponse)
def create_topic(
    topic_in: schemas.TopicCreate,
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.COORDINATOR, models.RoleEnum.ADMIN]))
):
    # Coordinators can only create topics for their own site
    # Admins could create global ones if we expose that, but for now site_id is user's site_id
    
    new_topic = models.Topic(
        name=topic_in.name,
        is_active=topic_in.is_active,
        site_id=current_user.site_id
    )
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)
    return new_topic

@router.get("/stats")
def get_topic_stats(
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.COORDINATOR, models.RoleEnum.GENERAL_COORDINATOR]))
):
    # Return count of sessions each topic is present in, filtered by the coordinator's site
    
    from sqlalchemy import func
    
    query = db.query(
        models.Topic.name, 
        func.count(models.AppointmentTopic.id).label("count")
    ).join(models.AppointmentTopic, models.Topic.id == models.AppointmentTopic.topic_id)\
     .join(models.Appointment, models.AppointmentTopic.appointment_id == models.Appointment.id)\
     .join(models.Case, models.Appointment.case_id == models.Case.id)
     
    if current_user.site_id:
        query = query.filter(models.Case.site_id == current_user.site_id)
        
    stats = query.group_by(models.Topic.name).all()
    
    return [{"topic": row.name, "count": row.count} for row in stats]
