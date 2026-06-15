from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from fastapi.responses import StreamingResponse
import pandas as pd
import io

import models
import auth
from database import get_db

router = APIRouter(
    prefix="/export",
    tags=["export"],
)
from typing import Optional

@router.get("/full-excel")
def export_full_excel(
    therapist_id: Optional[int] = None,
    career: Optional[str] = None,
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.GENERAL_COORDINATOR, models.RoleEnum.COORDINATOR]))
):
    cases_q = db.query(models.Case).join(models.Participant)
    
    if current_user.role == models.RoleEnum.COORDINATOR:
        cases_q = cases_q.filter(models.Case.site_id == current_user.site_id)
        
    if therapist_id:
        cases_q = cases_q.filter(models.Case.therapist_id == therapist_id)
        
    if career:
        cases_q = cases_q.filter(models.Participant.career.ilike(f"%{career}%"))
    
    cases_data = []
    sessions_data = []
    for case in cases_q.all():
        participant = case.participant
        therapist = db.query(models.User).filter(models.User.id == case.therapist_id).first() if case.therapist_id else None
        process_data = case.process_data
        
        c_dict = {
            "Case ID": case.id,
            "Participant ID": participant.id,
            "Nombre Alumno": participant.full_name,
            "No. Cuenta": participant.student_account,
            "Folio Anónimo": participant.anonymous_folio,
            "Correo": participant.email,
            "Facultad": participant.faculty,
            "Sede ID": case.site_id,
            "Estado Caso": case.status.value if case.status else "N/A",
            "Terapeuta": therapist.email if therapist else "Sin Asignar",
            "Total Sesiones Agendadas": len(case.sessions),
            "Sesiones Completadas": len([s for s in case.sessions if s.status == "completed"]),
            
            # Process Metadata
            "Fecha Solicitud": process_data.fecha_solicitud.strftime("%Y-%m-%d") if process_data and process_data.fecha_solicitud else "",
            "Fecha Inicio Tratamiento": process_data.fecha_inicio.strftime("%Y-%m-%d") if process_data and process_data.fecha_inicio else "",
            "Semestre Inicio": process_data.semestre_inicio if process_data else "",
            "Edad": process_data.edad if process_data else "",
            "Sexo": process_data.sexo if process_data else "",
            "Año que Cursa": process_data.ano_cursa if process_data else "",
            "Inasistencias": process_data.inasistencias if process_data else "",
            "Horas Padres/Tutores": process_data.horas_padres if process_data else "",
            "Horas Clínicas Semestre Actual": process_data.horas_clinicas_actual if process_data else "",
            "Horas Clínicas Semestre Anterior": process_data.horas_clinicas_anterior if process_data else "",
            "Sesiones de Seguimiento": process_data.sesiones_seguimiento if process_data else "",
            "Estatus Proceso": process_data.estatus_proceso if process_data else "",
            "Motivo Interrupción": process_data.motivo_interrupcion if process_data else "",
            "Observaciones Abandono/Suspensión": process_data.observaciones_abandono if process_data else "",
            "Fecha Finalización": process_data.fecha_finalizacion.strftime("%Y-%m-%d") if process_data and process_data.fecha_finalizacion else "",
            "Semestre Finalización": process_data.semestre_finalizacion if process_data else "",
            "Tuvo Intervención API": "Sí" if process_data and process_data.tuvo_intervencion_api else "No",
            "Número Sesiones API": process_data.sesiones_api if process_data else "",
            "Impresión Diagnóstica": process_data.impresion_diagnostica if process_data else "",
            "Internamientos Previos": "Sí" if process_data and process_data.internamientos_previos else "No",
            "Internamientos Previos Cantidad": process_data.internamientos_previos_cant if process_data else "",
            "Internamientos Durante": "Sí" if process_data and process_data.internamientos_durante else "No",
            "Internamientos Durante Cantidad": process_data.internamientos_durante_cant if process_data else "",
            "Canalización a Psiquiatría": "Sí" if process_data and process_data.canalizacion_psiquiatria else "No",
            "DX Psiquiatría": process_data.dx_psiquiatria if process_data else "",
            "Fecha Canalización Psiquiatría": process_data.fecha_canalizacion.strftime("%Y-%m-%d") if process_data and process_data.fecha_canalizacion else "",
            "Canalización a Otra Disciplina": "Sí" if process_data and process_data.canalizacion_otra else "No",
            "Canalización Otra Disciplina Cuál": process_data.canalizacion_otra_cual if process_data else "",
            "Referido a Terapeuta Externo": "Sí" if process_data and process_data.referido_externo else "No",
            "Intervención Espora Comunitaria": "Sí" if process_data and process_data.intervencion_espora_comunitaria else "No",
            "Intervención Espora Comunitaria En Qué Consistió": process_data.intervencion_espora_comunitaria_cual if process_data else ""
        }
        cases_data.append(c_dict)
        
        # Populate session info
        for s in case.sessions:
            issues_str = ""
            if s.worked_issues:
                issues_list = []
                for issue, val in s.worked_issues.items():
                    if val:
                        if isinstance(val, bool):
                            issues_list.append(issue)
                        elif isinstance(val, dict):
                            if val.get("checked"):
                                detail = val.get("detail") or val.get("specify") or val.get("description") or ""
                                if detail:
                                    issues_list.append(f"{issue} ({detail})")
                                else:
                                    issues_list.append(issue)
                        else:
                            issues_list.append(f"{issue}: {val}")
                issues_str = ", ".join(issues_list)
                
            sessions_data.append({
                "Case ID": case.id,
                "Nombre Alumno": participant.full_name,
                "Folio Anónimo": participant.anonymous_folio,
                "Fecha Sesión": s.session_date.strftime("%Y-%m-%d %H:%M") if s.session_date else "",
                "Modalidad": s.modality.value if s.modality else "N/A",
                "Estatus Cita": s.status,
                "Notas Clínicas / de Evolución": s.therapist_notes or "",
                "Problemáticas Trabajadas": issues_str
            })
            
    df_cases = pd.DataFrame(cases_data)
    df_sessions = pd.DataFrame(sessions_data)
    
    valid_case_ids = [c["Case ID"] for c in cases_data]
    valid_part_ids = [c["Participant ID"] for c in cases_data]
    
    if valid_case_ids or valid_part_ids:
        subs_q = db.query(models.FormSubmission).filter(
            (models.FormSubmission.case_id.in_(valid_case_ids)) | 
            (models.FormSubmission.participant_id.in_(valid_part_ids))
        )
    else:
        subs_q = db.query(models.FormSubmission).filter(False)
    templates_dict = {}
    for sub in subs_q.all():
        tpl_name = sub.template.name
        
        row = {
            "Submission ID": sub.id,
            "Participant ID": sub.participant_id,
            "Case ID": sub.case_id,
            "Fecha Emisión": sub.submitted_at.strftime("%Y-%m-%d %H:%M") if sub.submitted_at else ""
        }
        
        for val in sub.field_values:
            field_name = val.field.name
            row[field_name] = val.value_text
            
        # Include attachment filenames
        att_names = ", ".join([att.filename for att in sub.attachments]) if sub.attachments else ""
        row["Archivos Adjuntos"] = att_names
            
        if tpl_name not in templates_dict:
            templates_dict[tpl_name] = []
        templates_dict[tpl_name].append(row)
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if not df_cases.empty:
            df_cases.to_excel(writer, sheet_name='Casos y Alumnos', index=False)
        else:
            pd.DataFrame(["No hay datos"]).to_excel(writer, sheet_name='Casos y Alumnos', index=False)
            
        if not df_sessions.empty:
            df_sessions.to_excel(writer, sheet_name='Evoluciones y Sesiones', index=False)
        else:
            pd.DataFrame(["No hay sesiones registradas"]).to_excel(writer, sheet_name='Evoluciones y Sesiones', index=False)
            
        if not templates_dict:
            pd.DataFrame(["No hay formularios"]).to_excel(writer, sheet_name='Formularios Vacios', index=False)
            
        for tpl_name, tpl_rows in templates_dict.items():
            df_tpl = pd.DataFrame(tpl_rows)
            safe_name = tpl_name[:30].replace("/", "-")
            df_tpl.to_excel(writer, sheet_name=safe_name, index=False)
            
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="Exportacion_ESPORA.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/case/{case_id}")
def export_case_history(
    case_id: int,
    db: DBSession = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    from datetime import datetime
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # RBAC Validations
    if current_user.role == models.RoleEnum.THERAPIST and case.therapist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to export this case")
    if current_user.role == models.RoleEnum.COORDINATOR and case.site_id != current_user.site_id:
        raise HTTPException(status_code=403, detail="Not authorized to export this case")
        
    participant = case.participant
    proc = case.process_data
    therapist = db.query(models.User).filter(models.User.id == case.therapist_id).first() if case.therapist_id else None
    
    summary_data = {
        "Campo": [
            "ID de Caso", "Nombre del Paciente", "Folio Anónimo", "No. de Cuenta", "Correo", 
            "Facultad", "Estado del Caso", "Terapeuta", "Fecha de Solicitud del Proceso", 
            "Fecha de Inicio de Tratamiento", "Semestre de Inicio", "Edad", "Sexo", 
            "Año que Cursa", "Sesiones Totales (Asistidas)", "Inasistencias", 
            "Horas Padres/Tutores", "Horas Clínicas Semestre Actual", "Horas Clínicas Semestre Anterior", 
            "Sesiones de Seguimiento", "Estatus del Proceso", "Motivo Interrupción", 
            "Observaciones Abandono/Suspensión", "Fecha Finalización", "Semestre Finalización", 
            "Intervención API", "Sesiones API", "Impresión Diagnóstica", 
            "Internamientos Previos", "Cant. Internamientos Previos", 
            "Internamientos Durante", "Cant. Internamientos Durante",
            "Canalización a Psiquiatría", "DX Psiquiatría", "Fecha Canalización Psiquiatría",
            "Canalización a Otra Disciplina", "Canalización Otra Disciplina Cuál",
            "Referido a Terapeuta Externo", "Intervención Espora Comunitaria",
            "Intervención Espora Comunitaria En Qué Consistió"
        ],
        "Valor": [
            case.id, participant.full_name, participant.anonymous_folio, participant.student_account, participant.email,
            participant.faculty, case.status.value if case.status else "N/A", therapist.email if therapist else "Sin Asignar",
            proc.fecha_solicitud.strftime("%Y-%m-%d") if proc and proc.fecha_solicitud else "",
            proc.fecha_inicio.strftime("%Y-%m-%d") if proc and proc.fecha_inicio else "",
            proc.semestre_inicio if proc else "",
            proc.edad if proc else "",
            proc.sexo if proc else "",
            proc.ano_cursa if proc else "",
            proc.sesiones_totales if proc else "",
            proc.inasistencias if proc else "",
            proc.horas_padres if proc else "",
            proc.horas_clinicas_actual if proc else "",
            proc.horas_clinicas_anterior if proc else "",
            proc.sesiones_seguimiento if proc else "",
            proc.estatus_proceso if proc else "",
            proc.motivo_interrupcion if proc else "",
            proc.observaciones_abandono if proc else "",
            proc.fecha_finalizacion.strftime("%Y-%m-%d") if proc and proc.fecha_finalizacion else "",
            proc.semestre_finalizacion if proc else "",
            "Sí" if proc and proc.tuvo_intervencion_api else "No",
            proc.sesiones_api if proc else "",
            proc.impresion_diagnostica if proc else "",
            "Sí" if proc and proc.internamientos_previos else "No",
            proc.internamientos_previos_cant if proc else "",
            "Sí" if proc and proc.internamientos_durante else "No",
            proc.internamientos_durante_cant if proc else "",
            "Sí" if proc and proc.canalizacion_psiquiatria else "No",
            proc.dx_psiquiatria if proc else "",
            proc.fecha_canalizacion.strftime("%Y-%m-%d") if proc and proc.fecha_canalizacion else "",
            "Sí" if proc and proc.canalizacion_otra else "No",
            proc.canalizacion_otra_cual if proc else "",
            "Sí" if proc and proc.referido_externo else "No",
            "Sí" if proc and proc.intervencion_espora_comunitaria else "No",
            proc.intervencion_espora_comunitaria_cual if proc else ""
        ]
    }
    df_summary = pd.DataFrame(summary_data)
    
    sessions_list = []
    for s in sorted(case.sessions, key=lambda x: x.session_date if x.session_date else datetime.min):
        issues_str = ""
        if s.worked_issues:
            issues_list = []
            for issue, present in s.worked_issues.items():
                if present:
                    if isinstance(present, dict):
                        desc = present.get("description", "")
                        status = present.get("status", "Presente")
                        if status == "Presente" or status is True:
                            issues_list.append(f"{issue.upper()}" + (f" ({desc})" if desc else ""))
                    elif present is True or str(present).lower() == "true":
                        issues_list.append(issue.upper())
            issues_str = ", ".join(issues_list)
            
        sessions_list.append({
            "Session ID": s.id,
            "Fecha Sesión": s.session_date.strftime("%Y-%m-%d %H:%M") if s.session_date else "",
            "Modalidad": "En Línea" if s.modality == "online" else "Presencial",
            "Estatus Asistencia": s.status if s.status else "",
            "Notas de Evolución": s.therapist_notes if s.therapist_notes else "",
            "Problemáticas Abordadas": issues_str
        })
    df_sessions = pd.DataFrame(sessions_list)
    
    submissions_list = []
    case_subs = db.query(models.FormSubmission).filter(models.FormSubmission.case_id == case.id).all()
    for sub in sorted(case_subs, key=lambda x: x.submitted_at if x.submitted_at else datetime.min):
        submitted_by = db.query(models.User).filter(models.User.id == sub.submitted_by_id).first() if sub.submitted_by_id else None
        
        field_vals_list = []
        for val in sub.field_values:
            f_name = val.field.label if val.field else f"Field {val.form_field_id}"
            f_val = val.value_text if val.value_text else ""
            field_vals_list.append(f"{f_name}: {f_val}")
        field_vals_str = " | ".join(field_vals_list)
        
        att_names = ", ".join([att.filename for att in sub.attachments]) if sub.attachments else ""
        
        submissions_list.append({
            "Submission ID": sub.id,
            "Plantilla / Cuestionario": sub.template.name if sub.template else "Nota Libre / Cuestionario",
            "Fecha Emisión": sub.submitted_at.strftime("%Y-%m-%d %H:%M") if sub.submitted_at else "",
            "Registrado Por": submitted_by.email if submitted_by else "Sistema",
            "Respuestas / Detalles": field_vals_str,
            "Archivos Adjuntos": att_names
        })
    df_submissions = pd.DataFrame(submissions_list)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Resumen del Paciente', index=False)
        
        if not df_sessions.empty:
            df_sessions.to_excel(writer, sheet_name='Historial de Sesiones', index=False)
        else:
            pd.DataFrame(columns=["Session ID", "Fecha Sesión", "Modalidad", "Estatus Asistencia", "Notas de Evolución", "Problemáticas Abordadas"]).to_excel(writer, sheet_name='Historial de Sesiones', index=False)
            
        if not df_submissions.empty:
            df_submissions.to_excel(writer, sheet_name='Evaluaciones y Notas', index=False)
        else:
            pd.DataFrame(columns=["Submission ID", "Plantilla / Cuestionario", "Fecha Emisión", "Registrado Por", "Respuestas / Detalles", "Archivos Adjuntos"]).to_excel(writer, sheet_name='Evaluaciones y Notas', index=False)
            
    output.seek(0)
    
    # Safe filename with anonymous folio or name
    safe_identifier = participant.anonymous_folio if participant.anonymous_folio else f"caso_{case_id}"
    filename = f"historial_{safe_identifier}.xlsx"
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
