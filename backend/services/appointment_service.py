from sqlalchemy.orm import Session
from models import Appointment
from schemas import AppointmentCreate, AppointmentUpdate
from fastapi import HTTPException
from datetime import datetime

class AppointmentService:
    @staticmethod
    def _check_overlap(db: Session, therapist_id: int, start_time: datetime, end_time: datetime, exclude_id: int = None):
        query = db.query(Appointment).filter(
            Appointment.therapist_id == therapist_id,
            Appointment.status != "cancelled",
            Appointment.start_time < end_time,
            Appointment.end_time > start_time
        )
        if exclude_id:
            query = query.filter(Appointment.id != exclude_id)
            
        if query.first():
            raise HTTPException(status_code=400, detail="El horario seleccionado se empalma con otra cita existente.")

    @staticmethod
    def create_appointment(db: Session, apt_in: AppointmentCreate) -> Appointment:
        if apt_in.end_time <= apt_in.start_time:
            raise HTTPException(status_code=400, detail="La hora de fin debe ser mayor a la hora de inicio.")
            
        AppointmentService._check_overlap(db, apt_in.therapist_id, apt_in.start_time, apt_in.end_time)
        
        apt = Appointment(**apt_in.dict())
        db.add(apt)
        db.commit()
        db.refresh(apt)
        return apt

    @staticmethod
    def create_biweekly_protocol(db: Session, apt_in: AppointmentCreate, num_sessions: int = 12) -> list[Appointment]:
        if apt_in.end_time <= apt_in.start_time:
            raise HTTPException(status_code=400, detail="La hora de fin debe ser mayor a la hora de inicio.")
            
        # First, check for overlaps for all 12 proposed dates
        from datetime import timedelta
        delta = timedelta(days=14)
        
        appointments_to_create = []
        current_start = apt_in.start_time
        current_end = apt_in.end_time
        
        for i in range(num_sessions):
            # Will raise HTTPException if there is an overlap
            AppointmentService._check_overlap(db, apt_in.therapist_id, current_start, current_end)
            
            # Prepare the appointment object
            apt_data = apt_in.dict()
            apt_data['start_time'] = current_start
            apt_data['end_time'] = current_end
            
            apt = Appointment(**apt_data)
            appointments_to_create.append(apt)
            
            # Step forward 14 days
            current_start += delta
            current_end += delta
            
        # If we reach here, there are no overlaps in all 14 dates. We can save them all safely.
        for apt in appointments_to_create:
            db.add(apt)
            
        db.commit()
        for apt in appointments_to_create:
            db.refresh(apt)
            
        return appointments_to_create

    @staticmethod
    def update_appointment(db: Session, apt_id: int, apt_in: AppointmentUpdate) -> Appointment:
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        new_start = apt_in.start_time if apt_in.start_time else apt.start_time
        new_end = apt_in.end_time if apt_in.end_time else apt.end_time
        
        if new_end <= new_start:
            raise HTTPException(status_code=400, detail="La hora de fin debe ser mayor a la hora de inicio.")
            
        if apt_in.start_time or apt_in.end_time:
            AppointmentService._check_overlap(db, apt.therapist_id, new_start, new_end, exclude_id=apt.id)
            
        update_data = apt_in.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(apt, key, value)
            
        db.commit()
        db.refresh(apt)
        return apt

    @staticmethod
    def get_appointments_by_therapist(db: Session, therapist_id: int):
        return db.query(Appointment).filter(Appointment.therapist_id == therapist_id).all()
        
    @staticmethod
    def get_all_appointments(db: Session):
        return db.query(Appointment).all()
        
    @staticmethod
    def delete_appointment(db: Session, apt_id: int):
        apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
        if not apt:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        db.delete(apt)
        db.commit()
