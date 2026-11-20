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

def _send_welcome_email(to_email: str, role_label: str, generic_password: str, site_name: str = ""):
    import smtplib
    from email.message import EmailMessage
    from config import settings
    try:
        login_url = f"{settings.frontend_url.rstrip('/')}/login"
        sede_txt = f" para la entidad/sede {site_name}" if site_name else ""

        msg = EmailMessage()
        msg["Subject"] = f"Bienvenido/a a ESPORA - Acceso a tu cuenta de {role_label}"
        msg["From"] = settings.mail_sender
        msg["To"] = to_email

        plain_body = (
            f"Hola,\n\n"
            f"Se ha creado tu cuenta de {role_label}{sede_txt} en la Plataforma Clínica ESPORA.\n\n"
            f"Enlace de acceso: {login_url}\n"
            f"Usuario (Correo): {to_email}\n"
            f"Contraseña inicial: {generic_password}\n\n"
            f"Al ingresar, podrás cambiar tu contraseña en cualquier momento desde el botón 'Cambiar Contraseña' en la barra superior.\n\n"
            f"Saludos cordiales,\n"
            f"Coordinación ESPORA - UNAM"
        )
        html_body = f"""
        <div style="font-family: Arial, Helvetica, sans-serif; max-width: 580px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #00A5B8, #F39221); height: 6px;"></div>
            <div style="padding: 28px 32px; color: #0f172a;">
                <h2 style="margin: 0 0 12px 0; color: #00A5B8;">Bienvenido/a a ESPORA Psicológica</h2>
                <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.5;">
                    Se ha creado tu cuenta de <strong>{role_label}</strong>{sede_txt} en la Plataforma Clínica ESPORA.
                </p>
                <div style="background: #f0f9fa; border-left: 4px solid #00A5B8; padding: 14px 18px; border-radius: 6px; margin-bottom: 22px; font-size: 14px;">
                    <p style="margin: 0 0 6px 0;"><strong>Usuario (Correo):</strong> {to_email}</p>
                    <p style="margin: 0;"><strong>Contraseña inicial:</strong> <code style="background: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 14px;">{generic_password}</code></p>
                </div>
                <p style="text-align: center; margin: 24px 0;">
                    <a href="{login_url}" style="display: inline-block; background-color: #00A5B8; color: #ffffff; text-decoration: none; font-weight: bold; padding: 12px 26px; border-radius: 8px; font-size: 15px;">
                        Ingresar a la Plataforma ESPORA
                    </a>
                </p>
                <p style="font-size: 13px; color: #475569; line-height: 1.5;">
                    Si el botón no abre automáticamente, copia y pega este enlace en tu navegador:<br>
                    <a href="{login_url}" style="color: #00A5B8;">{login_url}</a>
                </p>
                <p style="font-size: 13px; color: #64748b; margin-top: 18px;">
                    Te recomendamos cambiar tu contraseña al iniciar sesión desde el botón <strong>Cambiar Contraseña</strong> en la barra superior.
                </p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 12px; color: #94a3b8; margin: 0;">Coordinación ESPORA - UNAM</p>
            </div>
        </div>
        """
        msg.set_content(plain_body)
        msg.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(settings.mail_server, settings.mail_port, timeout=10) as server:
            if settings.mail_use_tls:
                server.starttls()
            if settings.mail_username and settings.mail_password:
                server.login(settings.mail_username, settings.mail_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Aviso: No se pudo enviar correo de bienvenida a {to_email}: {e}")


@router.post("/therapists/quick", response_model=schemas.UserResponse)
def create_therapist_quick(
    user: schemas.TherapistQuickCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.COORDINATOR]))
):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")
        
    site_id = current_user.site_id if current_user.role == models.RoleEnum.COORDINATOR else user.site_id
    if not site_id:
         raise HTTPException(status_code=400, detail="Site ID must be provided by General Coordinators.")

    generic_pwd = "Espora2026!"
    hashed_password = auth.get_password_hash(generic_pwd)
    default_name = (user.full_name or "").strip() or user.email.split("@")[0].replace(".", " ").title()
    
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        role=models.RoleEnum.THERAPIST,
        site_id=site_id,
        is_active=True,
        full_name=default_name,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    site_obj = db.query(models.Site).filter(models.Site.id == site_id).first()
    _send_welcome_email(user.email, "Terapeuta", generic_pwd, site_obj.name if site_obj else "")
    return db_user

@router.post("/coordinators/quick", response_model=schemas.UserResponse)
def create_coordinator_quick(
    user: schemas.CoordinatorQuickCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR]))
):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")
        
    generic_pwd = "AdminEspora26!"
    hashed_password = auth.get_password_hash(generic_pwd)
    default_name = (user.full_name or "").strip() or user.email.split("@")[0].replace(".", " ").title()
    
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        role=models.RoleEnum.COORDINATOR,
        site_id=user.site_id,
        is_active=True,
        full_name=default_name,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    site_obj = db.query(models.Site).filter(models.Site.id == user.site_id).first()
    _send_welcome_email(user.email, "Coordinador/a de Sede", generic_pwd, site_obj.name if site_obj else "")
    return db_user

def _generate_recovery_code(email: str, hashed_pwd: str, window_offset: int = 0) -> str:
    import hmac
    import hashlib
    import time
    from config import settings
    # Ventanas de 15 minutos (900s)
    time_bucket = (int(time.time()) // 900) + window_offset
    msg = f"{email.lower().strip()}:{hashed_pwd}:{time_bucket}".encode("utf-8")
    digest = hmac.new(settings.secret_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return str(int(digest[:8], 16) % 1000000).zfill(6)


@router.post("/forgot-password")
def forgot_password(
    req: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    import smtplib
    from email.message import EmailMessage
    from config import settings

    email_clean = req.email.strip()
    db_user = db.query(models.User).filter(models.User.email.ilike(email_clean)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="No existe ninguna cuenta registrada con ese correo electrónico.")

    code = _generate_recovery_code(db_user.email, db_user.hashed_password, 0)
    msg = EmailMessage()
    msg.set_content(
        f"Hola {db_user.full_name or db_user.email},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña en la Plataforma Clínica ESPORA.\n\n"
        f"🔐 Tu código de verificación de 6 dígitos es: {code}\n"
        f"(Este código es válido por 30 minutos).\n\n"
        f"Ingresa este código en la ventana de recuperación de ESPORA junto con tu nueva contraseña.\n\n"
        f"Si tú no solicitaste este cambio, puedes ignorar este mensaje; tu contraseña actual seguirá intacta.\n\n"
        f"Saludos cordiales,\n"
        f"Coordinación ESPORA - UNAM"
    )
    msg["Subject"] = f"Código de recuperación de contraseña ({code}) - ESPORA"
    msg["From"] = settings.mail_sender
    msg["To"] = db_user.email

    try:
        with smtplib.SMTP(settings.mail_server, settings.mail_port, timeout=10) as server:
            if settings.mail_use_tls:
                server.starttls()
            if settings.mail_username and settings.mail_password:
                server.login(settings.mail_username, settings.mail_password)
            server.send_message(msg)
    except Exception as smtp_err:
        try:
            with smtplib.SMTP("mailpit", 1025, timeout=5) as local_srv:
                local_srv.send_message(msg)
        except Exception:
            raise HTTPException(status_code=500, detail=f"No se pudo enviar el correo de recuperación: {str(smtp_err)}")

    return {
        "status": "success",
        "message": f"Se ha enviado un código de 6 dígitos al correo {db_user.email}."
    }


@router.post("/reset-password")
def reset_password_with_code(
    req: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    email_clean = req.email.strip()
    db_user = db.query(models.User).filter(models.User.email.ilike(email_clean)).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="No existe ninguna cuenta registrada con ese correo electrónico.")

    valid_codes = [
        _generate_recovery_code(db_user.email, db_user.hashed_password, 0),
        _generate_recovery_code(db_user.email, db_user.hashed_password, -1),
    ]
    if req.code.strip() not in valid_codes:
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o ha expirado.")

    if not req.new_password or len(req.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres.")

    db_user.hashed_password = auth.get_password_hash(req.new_password.strip())
    db.commit()
    return {
        "status": "success",
        "message": "Contraseña restablecida exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."
    }


@router.post("/me/change-password")
def change_own_password(
    req: schemas.PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not auth.verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual (o llave genérica) es incorrecta.")
    if not req.new_password or len(req.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres.")
    current_user.hashed_password = auth.get_password_hash(req.new_password.strip())
    db.commit()
    return {"status": "success", "message": "Tu contraseña ha sido actualizada exitosamente."}

@router.get("/", response_model=List[schemas.UserResponse])
def read_users(
    skip: int = 0, limit: int = 200, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.COORDINATOR]))
):
    query = db.query(models.User)
    
    # Coordinators can only see users from their site
    if current_user.role == models.RoleEnum.COORDINATOR:
        query = query.filter(models.User.site_id == current_user.site_id)
        
    return query.offset(skip).limit(limit).all()

@router.get("/therapists", response_model=List[schemas.UserResponse])
def get_site_therapists(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    print(f"DEBUG THERAPISTS: User {current_user.email}, Role: {current_user.role}, Type: {type(current_user.role)}")
    if current_user.role not in [models.RoleEnum.ADMIN, models.RoleEnum.COORDINATOR, models.RoleEnum.GENERAL_COORDINATOR, "admin", "coordinator", "general_coordinator"]:
        raise HTTPException(status_code=403, detail=f"Not enough permissions. Role is {current_user.role}")

    query = db.query(models.User).filter(models.User.role == models.RoleEnum.THERAPIST)
    if not include_inactive:
        query = query.filter(models.User.is_active == True)
    
    if current_user.role in [models.RoleEnum.COORDINATOR, "coordinator"]:
        query = query.filter(models.User.site_id == current_user.site_id)
        
    return query.all()


@router.post("/therapists/{therapist_id}/deactivate-and-migrate")
def deactivate_therapist_and_migrate(
    therapist_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.COORDINATOR]))
):
    """
    Da de baja (desactiva) a un terapeuta y migra cada uno de sus pacientes
    junto con todo su historial clínico (sesiones, evaluaciones, notas de voz,
    citas programadas y datos de proceso) al terapeuta seleccionado manualmente
    para cada caso, o los regresa a Lista de Espera si el destino es null/'WAITLIST'.
    """
    therapist = db.query(models.User).filter(
        models.User.id == therapist_id,
        models.User.role == models.RoleEnum.THERAPIST
    ).first()
    if not therapist:
        raise HTTPException(status_code=404, detail="Terapeuta no encontrado.")

    if current_user.role == models.RoleEnum.COORDINATOR and therapist.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="No puedes dar de baja a un terapeuta de otra sede.")

    migrations_raw = payload.get("migrations") or {}
    # Normalize keys to int case_id
    migrations = {}
    for k, v in migrations_raw.items():
        try:
            cid = int(k)
        except Exception:
            continue
        if v is None or str(v).upper() in ("", "NONE", "WAITLIST"):
            migrations[cid] = None
        else:
            migrations[cid] = int(v)

    active_cases = db.query(models.Case).filter(
        models.Case.therapist_id == therapist_id,
        models.Case.status.in_([models.CaseStatusEnum.ASSIGNED, models.CaseStatusEnum.ACTIVE])
    ).all()

    # Validate every active case has a valid migration target
    migrated_count = 0
    waitlist_count = 0
    for c in active_cases:
        if c.id not in migrations:
            raise HTTPException(
                status_code=400,
                detail=f"Debes seleccionar un destino para el caso #{c.id} ({c.participant.full_name if c.participant else 'Paciente'})."
            )
        target_th_id = migrations[c.id]
        if target_th_id is None:
            c.therapist_id = None
            c.status = models.CaseStatusEnum.WAITING
            # Cancel/unassign future scheduled appointments for this case
            db.query(models.Appointment).filter(
                models.Appointment.case_id == c.id,
                models.Appointment.therapist_id == therapist_id,
                models.Appointment.status == "scheduled"
            ).update({"status": "cancelled"}, synchronize_session=False)
            waitlist_count += 1
        else:
            if target_th_id == therapist_id:
                raise HTTPException(status_code=400, detail="No puedes migrar pacientes al mismo terapeuta que se está dando de baja.")
            target_th = db.query(models.User).filter(
                models.User.id == target_th_id,
                models.User.role == models.RoleEnum.THERAPIST,
                models.User.is_active == True
            ).first()
            if not target_th:
                raise HTTPException(status_code=404, detail=f"El terapeuta destino (ID {target_th_id}) no existe o está inactivo.")
            if current_user.role == models.RoleEnum.COORDINATOR and target_th.site_id != current_user.site_id:
                raise HTTPException(status_code=403, detail="El terapeuta destino debe pertenecer a tu misma sede.")

            c.therapist_id = target_th_id
            # Transfer upcoming scheduled appointments to the new therapist so they appear in their calendar
            db.query(models.Appointment).filter(
                models.Appointment.case_id == c.id,
                models.Appointment.therapist_id == therapist_id,
                models.Appointment.status == "scheduled"
            ).update({"therapist_id": target_th_id}, synchronize_session=False)
            migrated_count += 1

    therapist.is_active = False
    db.commit()

    return {
        "status": "ok",
        "deactivated_therapist": therapist.full_name or therapist.email,
        "migrated_cases": migrated_count,
        "returned_to_waitlist": waitlist_count
    }

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

@router.get("/me/feedback/status", response_model=Dict[str, bool])
def get_feedback_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.THERAPIST]))
):
    import datetime
    current_year, current_week, _ = datetime.date.today().isocalendar()
    exists = db.query(models.TherapistFeedback).filter(
        models.TherapistFeedback.therapist_id == current_user.id,
        models.TherapistFeedback.year == current_year,
        models.TherapistFeedback.week == current_week
    ).first()
    return {"already_submitted": exists is not None}

@router.post("/me/feedback", response_model=schemas.TherapistFeedbackResponse)
def submit_feedback(
    feedback: schemas.TherapistFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.THERAPIST]))
):
    import datetime
    current_year, current_week, _ = datetime.date.today().isocalendar()
    
    # Check if already submitted to prevent duplicates
    exists = db.query(models.TherapistFeedback).filter(
        models.TherapistFeedback.therapist_id == current_user.id,
        models.TherapistFeedback.year == current_year,
        models.TherapistFeedback.week == current_week
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Feedback already submitted for this week")
        
    db_feedback = models.TherapistFeedback(
        therapist_id=current_user.id,
        year=current_year,
        week=current_week,
        q1_score=feedback.q1_score,
        q2_score=feedback.q2_score
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/feedback/report", response_model=List[Dict[str, Any]])
def get_feedback_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN, models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.COORDINATOR]))
):
    query = db.query(
        models.TherapistFeedback.id,
        models.TherapistFeedback.therapist_id,
        models.User.full_name.label("therapist_name"),
        models.User.site_id,
        models.Site.name.label("site_name"),
        models.TherapistFeedback.year,
        models.TherapistFeedback.week,
        models.TherapistFeedback.q1_score,
        models.TherapistFeedback.q2_score,
        models.TherapistFeedback.submitted_at
    ).join(
        models.User, models.TherapistFeedback.therapist_id == models.User.id
    ).join(
        models.Site, models.User.site_id == models.Site.id
    )

    if current_user.role == models.RoleEnum.COORDINATOR:
        query = query.filter(models.User.site_id == current_user.site_id)

    results = query.all()
    
    report = []
    for r in results:
        report.append({
            "id": r[0],
            "therapist_id": r[1],
            "therapist_name": r[2] or "Terapeuta Sin Nombre",
            "site_id": r[3],
            "site_name": r[4],
            "year": r[5],
            "week": r[6],
            "q1_score": r[7],
            "q2_score": r[8],
            "submitted_at": r[9].isoformat() if r[9] else None
        })
    return report
