from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from jose import JWTError, jwt

import models
import schemas
import auth
from database import get_db
from config import settings

router = APIRouter(
    prefix="/fields",
    tags=["Dynamic Forms"]
)

optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def get_optional_user(token: Optional[str] = Depends(optional_oauth2_scheme), db: Session = Depends(get_db)) -> Optional[models.User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email:
            return db.query(models.User).filter(models.User.email == email).first()
    except JWTError:
        return None
    return None

# --- TEMPLATES & FIELDS ---

@router.get("/templates", response_model=List[schemas.FormTemplateResponse])
def get_form_templates(db: Session = Depends(get_db)):
    """Obtener plantillas activas. Público para que los frontends puedan renderizarlas."""
    free_note = db.query(models.FormTemplate).filter(models.FormTemplate.name == "Nota Libre / Expediente Físico (Adjunto)").first()
    if not free_note:
        free_note = models.FormTemplate(
            name="Nota Libre / Expediente Físico (Adjunto)",
            description="Plantilla para adjuntar notas clínicas manuscritas, imágenes o archivos de texto libre.",
            is_active=True
        )
        db.add(free_note)
        db.commit()
        db.refresh(free_note)
        
    return db.query(models.FormTemplate).filter(models.FormTemplate.is_active == True).order_by(models.FormTemplate.id).all()

@router.get("/templates/{template_id}/fields", response_model=List[schemas.FormFieldResponse])
def get_template_fields(template_id: int, db: Session = Depends(get_db)):
    template = db.query(models.FormTemplate).filter(models.FormTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.fields

@router.post("/templates", response_model=schemas.FormTemplateResponse)
def create_form_template(
    template_in: schemas.FormTemplateCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR]))
):
    """Crea una nueva plantilla de formulario. Solo Admins."""
    db_template = models.FormTemplate(**template_in.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.post("/templates/{template_id}/fields", response_model=schemas.FormFieldResponse)
def create_form_field(
    template_id: int,
    field_in: schemas.FormFieldBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR]))
):
    """Agrega un campo/pregunta a una plantilla existente."""
    template = db.query(models.FormTemplate).filter(models.FormTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    db_field = models.FormField(**field_in.model_dump(), form_template_id=template_id)
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

# --- SUBMISSIONS ---

@router.post("/submissions", response_model=schemas.FormSubmissionResponse)
def create_submission(
    submission_in: schemas.FormSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user)
):
    """
    Enviar las respuestas de un formulario.
    Si se asocia a un caso, requiere autenticación y validación RBAC.
    Si es público (ej. ficha de ingreso), no requiere autenticación.
    """
    template = db.query(models.FormTemplate).filter(models.FormTemplate.id == submission_in.form_template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    # Check permissions if tied to a case
    if submission_in.case_id:
        case = db.query(models.Case).filter(models.Case.id == submission_in.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if current_user:
            if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to submit forms for this case")
            if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
                raise HTTPException(status_code=403, detail="Not authorized to submit forms for cases outside your site")
        else:
            # Only authenticated users can submit to a case
            raise HTTPException(status_code=401, detail="Authentication required to submit case forms")
            
    db_submission = models.FormSubmission(
        form_template_id=submission_in.form_template_id,
        participant_id=submission_in.participant_id,
        case_id=submission_in.case_id,
        session_id=submission_in.session_id,
        submitted_by_id=current_user.id if current_user else None
    )
    db.add(db_submission)
    db.flush() # get id to attach field values
    
    for field_val in submission_in.fields:
        db_val = models.FormFieldValue(
            form_submission_id=db_submission.id,
            form_field_id=field_val.form_field_id,
            value_text=field_val.value_text
        )
        db.add(db_val)
        
    if submission_in.attachments:
        for att in submission_in.attachments:
            db_att = models.FormSubmissionAttachment(
                form_submission_id=db_submission.id,
                filename=att.filename,
                content_type=att.content_type,
                file_data=att.file_data
            )
            db.add(db_att)
        
    db.commit()
    db.refresh(db_submission)
    return db_submission

@router.get("/submissions/case/{case_id}", response_model=List[schemas.FormSubmissionResponse])
def get_case_submissions(
    case_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Obtener todas las respuestas de formulario para un caso particular con validación RBAC."""
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # Validaciones RBAC
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this case's forms")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to view cases outside your site")
        
    submissions = db.query(models.FormSubmission).filter(models.FormSubmission.case_id == case_id).all()
    return submissions
