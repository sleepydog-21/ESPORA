from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict

import models
import schemas
import auth
from database import get_db

router = APIRouter(
    prefix="/fields",
    tags=["Dynamic Fields"]
)

@router.get("/", response_model=List[schemas.FieldDefinitionResponse])
def get_field_definitions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return db.query(models.FieldDefinition).filter(models.FieldDefinition.is_active == True).all()

@router.post("/", response_model=schemas.FieldDefinitionResponse)
def create_field_definition(
    field_in: schemas.FieldDefinitionCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role not in [models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR]:
        raise HTTPException(status_code=403, detail="Not authorized to create fields")
    
    db_field = db.query(models.FieldDefinition).filter_by(name=field_in.name).first()
    if db_field:
        raise HTTPException(status_code=400, detail="Field name already exists")
        
    new_field = models.FieldDefinition(**field_in.model_dump())
    db.add(new_field)
    db.commit()
    db.refresh(new_field)
    return new_field

@router.get("/case/{case_id}/values")
def get_case_field_values(
    case_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Check permissions
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to view cases outside your site")
        
    values = db.query(models.FieldValue).filter(models.FieldValue.participant_id == case.participant_id).all()
    
    # Format return as a dict mapping Field Name to Value string to be easy for frontend
    result = {}
    for val in values:
        field_def = db.query(models.FieldDefinition).filter(models.FieldDefinition.id == val.field_definition_id).first()
        if field_def:
            result[field_def.name] = val.value
            
    return result

@router.put("/case/{case_id}/values")
def update_case_field_values(
    case_id: int, 
    update_data: schemas.FieldValueUpdateBatch,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Check permissions
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this case")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit cases outside your site")
        
    # Process each field
    updates_made = 0
    for field_name, new_value in update_data.fields.items():
        field_def = db.query(models.FieldDefinition).filter(models.FieldDefinition.name == field_name).first()
        if not field_def:
            continue # ignore unknown fields
            
        current_val = db.query(models.FieldValue).filter(
            models.FieldValue.participant_id == case.participant_id,
            models.FieldValue.field_definition_id == field_def.id
        ).first()
        
        old_val_str = current_val.value if current_val else None
        
        # Don't stringify everything blindly if it hasn't changed.
        # Handle string conversion properly.
        new_val_str = str(new_value) if new_value is not None else None
        
        if old_val_str == new_val_str:
            continue
            
        if current_val:
            current_val.value = new_val_str
            current_val.updated_by_id = current_user.id
            audit_action = models.AuditActionEnum.UPDATE
        else:
            current_val = models.FieldValue(
                participant_id=case.participant_id,
                field_definition_id=field_def.id,
                value=new_val_str,
                updated_by_id=current_user.id
            )
            db.add(current_val)
            audit_action = models.AuditActionEnum.CREATE
            
        # Log to Audit
        audit = models.AuditLog(
            table_name="field_values",
            record_id=case.participant_id, # Can use participant_id as the anchor
            action=audit_action,
            old_value={"field": field_name, "val": old_val_str},
            new_value={"field": field_name, "val": new_val_str},
            user_id=current_user.id
        )
        db.add(audit)
        updates_made += 1
        
    db.commit()
    return {"message": "Success", "fields_updated": updates_made}
