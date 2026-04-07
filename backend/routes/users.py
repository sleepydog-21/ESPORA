from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.post("/", response_model=schemas.UserResponse)
def create_user(
    user: schemas.UserCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Coordinators can only create users for their own site
    if current_user.role == models.RoleEnum.COORDINATOR:
        user.site_id = current_user.site_id

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        site_id=user.site_id,
        is_active=user.is_active,
        full_name=user.full_name if hasattr(user, 'full_name') else None,
        phone=user.phone if hasattr(user, 'phone') else None,
        therapist_category=user.therapist_category if hasattr(user, 'therapist_category') else None
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/therapists/quick", response_model=schemas.UserResponse)
def create_therapist_quick(
    user: schemas.TherapistQuickCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.COORDINATOR]))
):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    site_id = current_user.site_id if current_user.role == models.RoleEnum.COORDINATOR else user.site_id
    if not site_id:
         raise HTTPException(status_code=400, detail="Site ID must be provided by General Coordinators.")

    hashed_password = auth.get_password_hash("Espora2026!") # Default temp password
    
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        role=models.RoleEnum.THERAPIST,
        site_id=site_id,
        is_active=True,
        full_name=user.full_name,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/coordinators/quick", response_model=schemas.UserResponse)
def create_coordinator_quick(
    user: schemas.CoordinatorQuickCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR]))
):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = auth.get_password_hash("AdminEspora26!") 
    
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        role=models.RoleEnum.COORDINATOR,
        site_id=user.site_id,
        is_active=True,
        full_name=user.full_name,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[schemas.UserResponse])
def read_users(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    query = db.query(models.User)
    
    # Coordinators can only see users from their site
    if current_user.role == models.RoleEnum.COORDINATOR:
        query = query.filter(models.User.site_id == current_user.site_id)
        
    return query.offset(skip).limit(limit).all()

@router.get("/therapists", response_model=List[schemas.UserResponse])
def get_site_therapists(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    print(f"DEBUG THERAPISTS: User {current_user.email}, Role: {current_user.role}, Type: {type(current_user.role)}")
    if current_user.role not in [models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR, "admin", "coordinator"]:
        raise HTTPException(status_code=403, detail=f"Not enough permissions. Role is {current_user.role}")

    query = db.query(models.User).filter(models.User.role == models.RoleEnum.THERAPIST)
    
    if current_user.role in [models.RoleEnum.COORDINATOR, "coordinator"]:
        query = query.filter(models.User.site_id == current_user.site_id)
        
    return query.all()

@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]))
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role == models.RoleEnum.COORDINATOR and db_user.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to update users for this site")
        
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    db.commit()
    db.refresh(db_user)
    return db_user
