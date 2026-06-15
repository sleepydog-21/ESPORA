import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models

def get_enum_val(val):
    if val is None:
        return ""
    if hasattr(val, "value"):
        return val.value
    return str(val)

def remove_tz(dt):
    if dt is None:
        return None
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def backup():
    db = SessionLocal()
    backup_dir = "/app/datos/respaldos"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(backup_dir, f"espora_respaldo_{timestamp}.xlsx")
    filepath_actual = os.path.join(backup_dir, "espora_respaldo_actual.xlsx")
    
    print(f"Iniciando respaldo de base de datos en: {filepath}...")
    
    try:
        # Extract tables
        users_q = db.query(models.User).all()
        df_users = pd.DataFrame([{
            "id": u.id, "email": u.email, "full_name": u.full_name, "role": get_enum_val(u.role),
            "site_id": u.site_id, "is_active": u.is_active
        } for u in users_q])
        
        participants_q = db.query(models.Participant).all()
        df_participants = pd.DataFrame([{
            "id": p.id, "student_account": p.student_account, "anonymous_folio": p.anonymous_folio,
            "full_name": p.full_name, "email": p.email, "phone": p.phone, "gender": p.gender,
            "career": p.career, "faculty": p.faculty, "site_id": p.site_id, "limesurvey_summary": p.limesurvey_summary
        } for p in participants_q])
        
        cases_q = db.query(models.Case).all()
        df_cases = pd.DataFrame([{
            "id": c.id, "participant_id": c.participant_id, "therapist_id": c.therapist_id,
            "site_id": c.site_id, "status": get_enum_val(c.status), "intake_source": c.intake_source,
            "created_at": remove_tz(c.created_at)
        } for c in cases_q])
        
        sessions_q = db.query(models.Session).all()
        df_sessions = pd.DataFrame([{
            "id": s.id, "case_id": s.case_id, "session_date": remove_tz(s.session_date),
            "status": get_enum_val(s.status), "modality": get_enum_val(s.modality), "notes": s.therapist_notes,
            "worked_issues": str(s.worked_issues) if s.worked_issues else ""
        } for s in sessions_q])
        
        process_q = db.query(models.CaseProcessData).all()
        df_process = pd.DataFrame([{
            "case_id": cp.case_id, "fecha_solicitud": remove_tz(cp.fecha_solicitud), "fecha_inicio": remove_tz(cp.fecha_inicio),
            "semestre_inicio": cp.semestre_inicio, "edad": cp.edad, "sexo": cp.sexo, "ano_cursa": cp.ano_cursa,
            "sesiones_totales": cp.sesiones_totales, "inasistencias": cp.inasistencias, "horas_padres": cp.horas_padres,
            "horas_clinicas_actual": cp.horas_clinicas_actual, "horas_clinicas_anterior": cp.horas_clinicas_anterior,
            "sesiones_seguimiento": cp.sesiones_seguimiento, "estatus_proceso": cp.estatus_proceso,
            "motivo_interrupcion": cp.motivo_interrupcion, "observaciones_abandono": cp.observaciones_abandono,
            "fecha_finalizacion": remove_tz(cp.fecha_finalizacion), "semestre_finalizacion": cp.semestre_finalizacion,
            "tuvo_intervencion_api": cp.tuvo_intervencion_api, "sesiones_api": cp.sesiones_api,
            "impresion_diagnostica": cp.impresion_diagnostica, "internamientos_previos": cp.internamientos_previos,
            "internamientos_previos_cant": cp.internamientos_previos_cant, "internamientos_durante": cp.internamientos_durante,
            "internamientos_durante_cant": cp.internamientos_durante_cant, "canalizacion_psiquiatria": cp.canalizacion_psiquiatria,
            "dx_psiquiatria": cp.dx_psiquiatria, "fecha_canalizacion": remove_tz(cp.fecha_canalizacion),
            "canalizacion_otra": cp.canalizacion_otra, "canalizacion_otra_cual": cp.canalizacion_otra_cual,
            "referido_externo": cp.referido_externo, "intervencion_espora_comunitaria": cp.intervencion_espora_comunitaria,
            "intervencion_espora_comunitaria_cual": cp.intervencion_espora_comunitaria_cual
        } for cp in process_q])
        
        templates_q = db.query(models.FormTemplate).all()
        df_templates = pd.DataFrame([{
            "id": t.id, "name": t.name, "description": t.description, "is_active": t.is_active
        } for t in templates_q])
        
        fields_q = db.query(models.FormField).all()
        df_fields = pd.DataFrame([{
            "id": f.id, "form_template_id": f.form_template_id, "name": f.name, "label": f.label,
            "field_type": get_enum_val(f.field_type), "is_required": f.is_required
        } for f in fields_q])
        
        submissions_q = db.query(models.FormSubmission).all()
        df_submissions = pd.DataFrame([{
            "id": sub.id, "form_template_id": sub.form_template_id, "participant_id": sub.participant_id,
            "case_id": sub.case_id, "session_id": sub.session_id, "submitted_by_id": sub.submitted_by_id,
            "submitted_at": remove_tz(sub.submitted_at)
        } for sub in submissions_q])
        
        values_q = db.query(models.FormFieldValue).all()
        df_values = pd.DataFrame([{
            "id": v.id, "form_submission_id": v.form_submission_id, "form_field_id": v.form_field_id,
            "value_text": v.value_text
        } for v in values_q])
        
        attachments_q = db.query(models.FormSubmissionAttachment).all()
        df_attachments = pd.DataFrame([{
            "id": a.id, "form_submission_id": a.form_submission_id, "filename": a.filename,
            "content_type": a.content_type, "file_data_length": len(a.file_data) if a.file_data else 0
        } for a in attachments_q])
        
        audits_q = db.query(models.AuditLog).all()
        df_audits = pd.DataFrame([{
            "id": ad.id, "table_name": ad.table_name, "record_id": ad.record_id,
            "action": get_enum_val(ad.action), "user_id": ad.user_id,
            "timestamp": remove_tz(ad.timestamp), "old_value": str(ad.old_value) if ad.old_value else "",
            "new_value": str(ad.new_value) if ad.new_value else ""
        } for ad in audits_q])
        
        # Save to excel files
        for fpath in [filepath, filepath_actual]:
            with pd.ExcelWriter(fpath, engine='openpyxl') as writer:
                df_users.to_excel(writer, sheet_name='Usuarios_Terapeutas', index=False)
                df_participants.to_excel(writer, sheet_name='Alumnos_Consultantes', index=False)
                df_cases.to_excel(writer, sheet_name='Casos', index=False)
                df_sessions.to_excel(writer, sheet_name='Sesiones_Evoluciones', index=False)
                df_process.to_excel(writer, sheet_name='Control_Proceso', index=False)
                df_templates.to_excel(writer, sheet_name='Plantillas_Cuestionarios', index=False)
                df_fields.to_excel(writer, sheet_name='Campos_Formularios', index=False)
                df_submissions.to_excel(writer, sheet_name='Sumisiones', index=False)
                df_values.to_excel(writer, sheet_name='Valores_Campos', index=False)
                df_attachments.to_excel(writer, sheet_name='Adjuntos_Metadatos', index=False)
                df_audits.to_excel(writer, sheet_name='Auditoria_Cambios', index=False)
                
        print(f"Respaldo completado exitosamente en: {filepath} y {filepath_actual}.")
    except Exception as e:
        print(f"Error al realizar respaldo: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backup()
