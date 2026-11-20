from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from sqlalchemy import func
from datetime import datetime, timedelta

def check_alert_thresholds():
    db = SessionLocal()
    try:
        alerts = db.query(models.AlertSetting).filter(models.AlertSetting.is_active == True).all()
        if not alerts: 
            return
            
        waitlist_counts = db.query(
            models.Case.site_id,
            func.count(models.Case.id).label("count")
        ).filter(models.Case.status == models.CaseStatusEnum.WAITING).group_by(models.Case.site_id).all()
        
        waitlist_dict = {w[0]: w[1] for w in waitlist_counts}
        total_waitlist = sum(waitlist_dict.values())
        
        for rule in alerts:
            current_val = 0
            if rule.metric_name == "waitlist_size":
                if rule.site_id:
                    current_val = waitlist_dict.get(rule.site_id, 0)
                else:
                    current_val = total_waitlist
                    
            trigger = False
            if rule.operator == ">" and current_val > rule.threshold_value:
                trigger = True
            elif rule.operator == "==" and current_val == rule.threshold_value:
                trigger = True
                
            if trigger:
                # Anti-spam: check if notification exists in last 24h
                recent = db.query(models.Notification).filter(
                    models.Notification.message.like(f"%{rule.metric_name}%"),
                    models.Notification.site_id == rule.site_id,
                    models.Notification.created_at > datetime.utcnow() - timedelta(hours=24)
                ).first()
                
                if not recent:
                    sede_str = f"Sede {rule.site_id}" if rule.site_id else "Global"
                    msg = f"ALERTA ({sede_str}): {rule.metric_name} alcanzó {current_val} (Regla: {rule.operator} {rule.threshold_value})"
                    
                    n = models.Notification(
                        message=msg,
                        is_read=False,
                        site_id=rule.site_id,
                        user_id=rule.created_by_id
                    )
                    db.add(n)
        db.commit()
    except Exception as e:
        print("Scheduler error:", e)
    finally:
        db.close()

def check_dropout_risk():
    db = SessionLocal()
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Encuentra casos activos cuya última sesión fue hace más de 30 días o nunca han tenido
        active_cases = db.query(models.Case).filter(models.Case.status == models.CaseStatusEnum.ACTIVE).all()
        
        for c in active_cases:
            last_session = db.query(models.Session).filter(models.Session.case_id == c.id).order_by(models.Session.session_date.desc()).first()
            if (not last_session and c.updated_at and c.updated_at < thirty_days_ago) or (last_session and last_session.session_date and last_session.session_date.replace(tzinfo=None) < thirty_days_ago):
                # Deserción detectada. Avisar si no se ha avisado en una semana
                recent_alert = db.query(models.Notification).filter(
                    models.Notification.message.like(f"%Riesgo de Deserción: Caso #{c.id}%"),
                    models.Notification.created_at > datetime.utcnow() - timedelta(days=7)
                ).first()
                if not recent_alert:
                    coord = db.query(models.User).filter(models.User.role == models.RoleEnum.GENERAL_COORDINATOR).first()
                    msg = f"⚠️ Riesgo de Deserción: Caso #{c.id} (Terapeuta asignado no ha reportado sesión en >30 días)."
                    n = models.Notification(message=msg, is_read=False, site_id=c.site_id, user_id=coord.id if coord else c.therapist_id)
                    db.add(n)
        db.commit()
    except Exception as e:
        print("Dropout tracker error:", e)
    finally:
        db.close()

def run_limesurvey_sync():
    db = SessionLocal()
    try:
        from services.limesurvey_service import limesurvey_service
        report = limesurvey_service.sync_responses(survey_id=None, db=db)
        new_c = report.get("new_cases", 0)
        new_f = report.get("followup_submissions", 0)
        if new_c > 0 or new_f > 0:
            print(f"[Scheduler LimeSurvey] Sincronizados {new_c} nuevos casos y {new_f} cuestionarios de seguimiento.")
    except Exception as e:
        print("Scheduler LimeSurvey Sync warning:", e)
    finally:
        db.close()

def send_appointment_reminders():
    """
    Envía automáticamente un correo de recordatorio ~1 día antes (ventana 20h-28h)
    a cada paciente con cita programada en Appointment o Session.
    Usa un marcador idempotente en Notification para no duplicar envíos.
    """
    import smtplib
    from email.message import EmailMessage
    from config import settings

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        window_start = now + timedelta(hours=20)
        window_end = now + timedelta(hours=28)

        # Recolectar citas programadas desde Appointment y Session evitando duplicados por (case_id, fecha-hora)
        candidates = {}

        appts = db.query(models.Appointment).filter(
            models.Appointment.status == "scheduled",
            models.Appointment.case_id.isnot(None),
            models.Appointment.start_time >= window_start,
            models.Appointment.start_time <= window_end
        ).all()

        for a in appts:
            dt_naive = a.start_time.replace(tzinfo=None) if a.start_time.tzinfo else a.start_time
            slot_key = dt_naive.strftime("%Y%m%d_%H%M")
            candidates[(a.case_id, slot_key)] = {
                "case_id": a.case_id,
                "dt": dt_naive,
                "modality": "Presencial / En línea (confirmar con tu terapeuta)",
                "therapist_id": a.therapist_id,
            }

        sessions = db.query(models.Session).filter(
            models.Session.status == "scheduled",
            models.Session.session_date >= window_start,
            models.Session.session_date <= window_end
        ).all()

        modality_labels = {
            "online": "En Línea",
            "in_person": "Presencial",
        }
        for s in sessions:
            dt_naive = s.session_date.replace(tzinfo=None) if s.session_date.tzinfo else s.session_date
            slot_key = dt_naive.strftime("%Y%m%d_%H%M")
            mod_val = s.modality.value if hasattr(s.modality, "value") else str(s.modality or "")
            mod_label = modality_labels.get(mod_val.lower(), "Confirmar con tu terapeuta")
            key = (s.case_id, slot_key)
            if key not in candidates:
                candidates[key] = {
                    "case_id": s.case_id,
                    "dt": dt_naive,
                    "modality": mod_label,
                    "therapist_id": None,
                }
            else:
                candidates[key]["modality"] = mod_label

        if not candidates:
            return

        sent_count = 0
        for (case_id, slot_key), info in candidates.items():
            marker = f"[REMINDER_SENT:case:{case_id}:{slot_key}]"
            already = db.query(models.Notification).filter(
                models.Notification.message == marker
            ).first()
            if already:
                continue

            case_obj = db.query(models.Case).filter(models.Case.id == case_id).first()
            if not case_obj or not case_obj.participant or not case_obj.participant.email:
                continue

            patient_email = case_obj.participant.email.strip()
            if "@" not in patient_email:
                continue

            patient_name = case_obj.participant.full_name or "Consultante"
            th_id = info["therapist_id"] or case_obj.therapist_id
            therapist_obj = db.query(models.User).filter(models.User.id == th_id).first() if th_id else None
            therapist_name = (therapist_obj.full_name or therapist_obj.email) if therapist_obj else "Tu terapeuta ESPORA"
            site_name = case_obj.site.name if case_obj.site else "ESPORA - UNAM"

            dt_obj = info["dt"]
            fecha_str = dt_obj.strftime("%d/%m/%Y")
            hora_str = dt_obj.strftime("%H:%M")

            try:
                msg = EmailMessage()
                msg["Subject"] = f"Recordatorio de cita ESPORA mañana {fecha_str} a las {hora_str} hrs"
                msg["From"] = settings.mail_sender
                msg["To"] = patient_email

                plain_body = (
                    f"Hola {patient_name},\n\n"
                    f"Te recordamos que tienes una sesión psicológica programada en ESPORA para mañana:\n\n"
                    f"Fecha: {fecha_str}\n"
                    f"Hora: {hora_str} hrs\n"
                    f"Terapeuta: {therapist_name}\n"
                    f"Sede: {site_name}\n"
                    f"Modalidad: {info['modality']}\n\n"
                    f"Si por algún motivo no puedes asistir o necesitas reagendar, por favor avisa con anticipación a tu terapeuta.\n\n"
                    f"Saludos cordiales,\n"
                    f"Programa ESPORA Psicológica - UNAM"
                )
                html_body = f"""
                <div style="font-family: Arial, Helvetica, sans-serif; max-width: 560px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #00A5B8, #F39221); height: 6px;"></div>
                    <div style="padding: 26px 30px; color: #0f172a;">
                        <h2 style="margin: 0 0 10px 0; color: #00A5B8;">Recordatorio de tu cita en ESPORA</h2>
                        <p style="font-size: 15px; margin: 0 0 16px 0;">Hola <strong>{patient_name}</strong>,</p>
                        <p style="font-size: 14px; color: #334155; margin: 0 0 18px 0;">
                            Te recordamos que tienes una sesión psicológica programada para <strong>mañana</strong>:
                        </p>
                        <div style="background: #f0f9fa; border-left: 4px solid #00A5B8; padding: 14px 18px; border-radius: 6px; font-size: 14px; line-height: 1.7;">
                            <div><strong>Fecha:</strong> {fecha_str}</div>
                            <div><strong>Hora:</strong> {hora_str} hrs</div>
                            <div><strong>Terapeuta:</strong> {therapist_name}</div>
                            <div><strong>Sede:</strong> {site_name}</div>
                            <div><strong>Modalidad:</strong> {info['modality']}</div>
                        </div>
                        <p style="font-size: 13px; color: #64748b; margin-top: 18px;">
                            Si no puedes asistir o necesitas reagendar, por favor comunícate con anticipación con tu terapeuta.
                        </p>
                        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                        <p style="font-size: 12px; color: #94a3b8; margin: 0;">Programa ESPORA Psicológica - UNAM</p>
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

                db.add(models.Notification(
                    message=marker,
                    is_read=True,
                    site_id=case_obj.site_id,
                    user_id=th_id
                ))
                db.commit()
                sent_count += 1
            except Exception as mail_err:
                print(f"[Scheduler Recordatorios] Error enviando a {patient_email}: {mail_err}")

        if sent_count > 0:
            print(f"[Scheduler Recordatorios] Se enviaron {sent_count} recordatorios de citas (1 día antes).")
    except Exception as e:
        print("Scheduler appointment reminders error:", e)
    finally:
        db.close()

def run_db_backup():
    try:
        from scripts.backup_db import backup
        backup()
    except Exception as e:
        print("Scheduler DB Backup failed:", e)

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Runs every minute for demonstration reactivity
    scheduler.add_job(check_alert_thresholds, 'interval', minutes=1)
    # Auto-sync LimeSurvey surveys (118334, 228334, 338334) every 5 minutes
    scheduler.add_job(run_limesurvey_sync, 'interval', minutes=5)
    # Automated email reminders 1 day before scheduled appointments (checked every 30 min)
    scheduler.add_job(send_appointment_reminders, 'interval', minutes=30)
    # Drop-out detector runs every 1 hour realistically
    scheduler.add_job(check_dropout_risk, 'interval', hours=1)
    # Database backup runs every 12 hours
    scheduler.add_job(run_db_backup, 'interval', hours=12)
    scheduler.start()
    
    # Run an initial backup on startup
    try:
        run_db_backup()
    except Exception as e:
        print("Initial DB Backup failed:", e)
        
    return scheduler
