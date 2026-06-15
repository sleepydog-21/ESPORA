from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import RoleEnum
from schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentTopicCreate
from services.appointment_service import AppointmentService
from auth import get_current_user

router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/", response_model=List[AppointmentResponse])
def get_appointments(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role in [RoleEnum.ADMIN, RoleEnum.GENERAL_COORDINATOR]:
        return AppointmentService.get_all_appointments(db)
    elif current_user.role == RoleEnum.COORDINATOR:
        from models import Appointment, User
        return db.query(Appointment).join(User, Appointment.therapist_id == User.id).filter(
            User.site_id == current_user.site_id
        ).all()
    elif current_user.role == RoleEnum.THERAPIST:
        return AppointmentService.get_appointments_by_therapist(db, current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Not authorized to view appointments")

@router.post("/", response_model=AppointmentResponse)
def create_appointment(apt_in: AppointmentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role != RoleEnum.COORDINATOR and apt_in.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot create appointments for another therapist")
    return AppointmentService.create_appointment(db, apt_in)

@router.post("/biweekly", response_model=List[AppointmentResponse])
def create_biweekly_appointment(apt_in: AppointmentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role != RoleEnum.COORDINATOR and apt_in.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot create appointments for another therapist")
    return AppointmentService.create_biweekly_protocol(db, apt_in)

@router.patch("/{apt_id}", response_model=AppointmentResponse)
def update_appointment(apt_id: int, apt_in: AppointmentUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # To check permissions, we would ideally fetch first, but for simplicity we rely on the service
    from models import Appointment
    apt = db.query(Appointment).filter_by(id=apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != RoleEnum.COORDINATOR and apt.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot edit another therapist's appointment")
        
    return AppointmentService.update_appointment(db, apt_id, apt_in)

@router.delete("/{apt_id}")
def delete_appointment(apt_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    from models import Appointment
    apt = db.query(Appointment).filter_by(id=apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != RoleEnum.COORDINATOR and apt.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another therapist's appointment")
        
    AppointmentService.delete_appointment(db, apt_id)
    return {"detail": "Appointment deleted successfully"}

@router.post("/{apt_id}/topics", response_model=AppointmentResponse)
def set_appointment_topics(
    apt_id: int,
    payload: AppointmentTopicCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from models import Appointment, AppointmentTopic
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if current_user.role == RoleEnum.THERAPIST and apt.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # clear existing topics
    db.query(AppointmentTopic).filter(AppointmentTopic.appointment_id == apt_id).delete()
    
    # add new topics
    for topic_id in payload.topic_ids:
        st = AppointmentTopic(appointment_id=apt_id, topic_id=topic_id)
        db.add(st)
        
    db.commit()
    db.refresh(apt)
    return apt
