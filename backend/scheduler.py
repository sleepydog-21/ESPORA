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
            if (not last_session and c.updated_at < thirty_days_ago) or (last_session and last_session.session_date.replace(tzinfo=None) < thirty_days_ago):
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

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Runs every minute for demonstration reactivity
    scheduler.add_job(check_alert_thresholds, 'interval', minutes=1)
    # Drop-out detector runs every 1 hour realistically
    scheduler.add_job(check_dropout_risk, 'interval', hours=1)
    scheduler.start()
    return scheduler
