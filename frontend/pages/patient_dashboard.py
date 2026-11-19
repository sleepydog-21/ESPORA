import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc
import requests
import os
from datetime import datetime
import pandas as pd

dash.register_page(__name__, path_template='/patient/<case_id>', name='Patient Dashboard')

API_URL = os.getenv("API_URL", "http://localhost:8000")

def layout(case_id=None, **kwargs):
    if not case_id:
        return html.Div("No se especificó caso.")

    return dbc.Container([
        dcc.Location(id="patient-url"),
        dcc.Store(id="current-case-id", data=case_id),
        
        dbc.Row([
            dbc.Col(html.H2(id="patient-title", className="my-4 fw-bold text-primary"), width=6),
            dbc.Col([
                dbc.Button("Volver al Panel", href="/therapist", color="secondary", className="mt-4 float-end glass-btn ms-2"),
                dbc.Button("🚨 Derivar de API a Lista de Espera", id="btn-refer-api", color="warning", className="mt-4 float-end glass-btn ms-2 fw-semibold"),
                dbc.Button("✉️ Enviar Correo", id="btn-open-email-modal", color="primary", className="mt-4 float-end glass-btn ms-2"),
                dbc.Button("📥 Descargar Historial", id="btn-download-history", color="info", className="mt-4 float-end glass-btn"),
                dcc.Download(id="download-history-file")
            ], width=6)
        ]),
        dbc.Alert(id="refer-api-alert", is_open=False, duration=8000, className="mb-3 fw-semibold"),
        
        dbc.Row([
            # Left Column: Profile and Submission Forms
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Resumen del Paciente")),
                    dbc.CardBody([
                        html.Div(id="patient-info-content"),
                    ])
                ], className="mb-4 shadow-sm border-0 glass-card"),
                
                # Anexo Rápido (Nota / Foto / Archivo)
                dbc.Card([
                    dbc.CardHeader(html.H5("Anexo Rápido (Nota / Foto / Archivo)")),
                    dbc.CardBody([
                        dbc.Textarea(id="quick-submission-free-notes", placeholder="Escribe aquí notas clínicas libres, observaciones o transcripción...", rows=3, className="mb-3"),
                        dcc.Upload(
                            id="quick-submission-upload",
                            children=html.Div(["Arrastra y suelta o selecciona un archivo (Imagen, PDF, Texto)"]),
                            style={
                                'width': '100%',
                                'height': '50px',
                                'lineHeight': '50px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'marginBottom': '10px',
                                'cursor': 'pointer'
                            },
                            multiple=False
                        ),
                        html.Div(id="quick-submission-upload-preview", className="mb-2 text-muted small"),
                        dcc.Store(id="quick-submission-upload-store", data=None),
                        dbc.Button("💾 Anexar al Expediente", id="btn-submit-quick-submission", color="success", className="w-100"),
                        dbc.Alert(id="quick-submission-alert", is_open=False, color="success", className="mt-3")
                    ])
                ], className="mb-4 shadow-sm border-0 glass-card"),
                
                dbc.Card([
                    dbc.CardHeader(html.H5("Historial de Evaluaciones Clínicas")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(dbc.Button("➕ Nueva Captura Clínica", id="btn-new-submission", color="primary", className="w-100 mb-2"), width=12, md=6),
                            dbc.Col(dbc.Button("🔄 Sincronizar LimeSurvey", id="btn-sync-patient-ls", color="outline-primary", className="w-100 mb-2"), width=12, md=6),
                        ], className="mb-2"),
                        dbc.Alert(id="patient-ls-sync-alert", is_open=False, duration=6000, className="small py-2 mb-3"),
                        dcc.Store(id="patient-ls-sync-trigger", data=0),
                        dcc.Loading(
                            type="circle",
                            children=html.Div(id="submissions-timeline-container", className="mt-3")
                        )
                    ])
                ], className="mb-4 shadow-sm border-0 glass-card")
            ], width=12, md=6),
            
            # Right Column: Sessions
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(dbc.Row([
                        dbc.Col(html.H5("Línea de Tiempo de Sesiones")),
                        dbc.Col(dbc.Button("Agendar Única", id="btn-open-schedule", color="primary", size="sm", className="float-end"), width="auto")
                    ])),
                    dbc.CardBody([
                        html.Div(id='sessions-timeline-container', style={'maxHeight': '600px', 'overflowY': 'auto'})
                    ])
                ], className="shadow-sm border-0 glass-card")
            ], width=12, md=6)
        ]),
        
        # Row at the bottom: Process Data Control Form
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Datos de Control del Proceso Terapéutico (Expediente Clínico)")),
                    dbc.CardBody([
                        html.P("Completa y modifica las variables del proceso. Los campos numéricos y abiertos se autocompletarán con la información registrada pero se pueden modificar en vivo.", className="text-muted small mb-4"),
                        
                        dbc.Row([
                            # Column 1: Demographics and Process start
                            dbc.Col([
                                html.H6("Fechas y Demografía", className="text-primary fw-bold mb-3 border-bottom pb-1"),
                                
                                dbc.Label("Fecha de Solicitud del Proceso"),
                                dbc.Input(id="proc-fecha-solicitud", type="date", className="mb-2"),
                                
                                dbc.Label("Fecha de Inicio de Tratamiento"),
                                dbc.Input(id="proc-fecha-inicio", type="date", className="mb-2"),
                                
                                dbc.Label("Semestre de Inicio"),
                                dbc.Input(id="proc-semestre-inicio", type="text", placeholder="Ej. 2026-1", className="mb-2"),
                                
                                dbc.Label("Edad"),
                                dbc.Input(id="proc-edad", type="number", min=0, className="mb-2"),
                                
                                dbc.Label("Sexo"),
                                dbc.Select(id="proc-sexo", options=[
                                    {"label": "Femenino", "value": "Femenino"},
                                    {"label": "Masculino", "value": "Masculino"},
                                    {"label": "Otro", "value": "Otro"}
                                ], placeholder="Selecciona...", className="mb-2"),
                                
                                dbc.Label("Año que cursa"),
                                dbc.Input(id="proc-ano-cursa", type="number", min=1, className="mb-2"),
                            ], width=12, md=4),
                            
                            # Column 2: Session counts, hours and process status
                            dbc.Col([
                                html.H6("Sesiones, Horas y Estatus", className="text-primary fw-bold mb-3 border-bottom pb-1"),
                                
                                dbc.Label("Sesiones Totales (Asistidas)"),
                                dbc.Input(id="proc-sesiones-totales", type="number", min=0, className="mb-2"),
                                
                                dbc.Label("Inasistencias"),
                                dbc.Input(id="proc-inasistencias", type="number", min=0, className="mb-2"),
                                
                                dbc.Label("Horas de Entrevista con Padres/Tutores"),
                                dbc.Input(id="proc-horas-padres", type="number", min=0, step=0.5, className="mb-2"),
                                
                                dbc.Label("Horas Clínicas Semestre ACTUAL (asista o no)"),
                                dbc.Input(id="proc-horas-clinicas-actual", type="number", min=0, className="mb-2"),
                                
                                dbc.Label("Horas Clínicas Semestre ANTERIOR (asista o no)"),
                                dbc.Input(id="proc-horas-clinicas-anterior", type="number", min=0, className="mb-2"),
                                
                                dbc.Label("Sesiones de Seguimiento"),
                                dbc.Input(id="proc-sesiones-seguimiento", type="number", min=0, className="mb-2"),
                                
                                dbc.Label("Estatus del Proceso"),
                                dbc.Select(id="proc-estatus-proceso", options=[
                                    {"label": "No respondió correo", "value": "No respondió correo"},
                                    {"label": "En tratamiento", "value": "En tratamiento"},
                                    {"label": "Interrupción interna", "value": "Interrupción interna"},
                                    {"label": "Interrupción externa", "value": "Interrupción externa"},
                                    {"label": "Abandono", "value": "Abandono"},
                                    {"label": "Suspensión", "value": "Suspensión"}
                                ], placeholder="Selecciona...", className="mb-2"),
                                
                                html.Div([
                                    dbc.Label("Motivo de la Interrupción"),
                                    dbc.Textarea(id="proc-motivo-interrupcion", rows=2, placeholder="Explicar motivo de interrupción...")
                                ], id="div-proc-interrupcion", style={"display": "none"}, className="mb-2"),
                                
                                html.Div([
                                    dbc.Label("Observaciones sobre el Abandono / Suspensión"),
                                    dbc.Textarea(id="proc-observaciones-abandono", rows=2, placeholder="Observaciones sobre abandono...")
                                ], id="div-proc-abandono", style={"display": "none"}, className="mb-2"),
                            ], width=12, md=4),
                            
                            # Column 3: API intervention, Diagnoses, Channeling
                            dbc.Col([
                                html.H6("Canalizaciones y Apoyos Especiales", className="text-primary fw-bold mb-3 border-bottom pb-1"),
                                
                                dbc.Label("Fecha de Finalización del Tratamiento"),
                                dbc.Input(id="proc-fecha-finalizacion", type="date", className="mb-2"),
                                
                                dbc.Label("Semestre de Finalización"),
                                dbc.Input(id="proc-semestre-finalizacion", type="text", placeholder="Ej. 2026-2", className="mb-2"),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Intervención API"),
                                        dbc.Select(id="proc-tuvo-intervencion-api", options=[
                                            {"label": "Sí", "value": "true"},
                                            {"label": "No", "value": "false"}
                                        ], placeholder="Selecciona...", className="mb-2"),
                                    ]),
                                    dbc.Col([
                                        dbc.Label("Sesiones con API"),
                                        dbc.Input(id="proc-sesiones-api", type="number", min=0, className="mb-2"),
                                    ])
                                ]),
                                
                                dbc.Label("Impresión Diagnóstica"),
                                dbc.Textarea(id="proc-impresion-diagnostica", rows=2, className="mb-2", placeholder="Campo abierto..."),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Internamientos Previos"),
                                        dbc.Select(id="proc-internamientos-previos", options=[
                                            {"label": "Sí", "value": "true"},
                                            {"label": "No", "value": "false"}
                                        ], placeholder="Selecciona...", className="mb-2"),
                                    ]),
                                    dbc.Col([
                                        dbc.Label("¿Cuántos?"),
                                        dbc.Input(id="proc-internamientos-previos-cant", type="number", min=0, className="mb-2"),
                                    ])
                                ]),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Internamientos Durante"),
                                        dbc.Select(id="proc-internamientos-durante", options=[
                                            {"label": "Sí", "value": "true"},
                                            {"label": "No", "value": "false"}
                                        ], placeholder="Selecciona...", className="mb-2"),
                                    ]),
                                    dbc.Col([
                                        dbc.Label("¿Cuántos?"),
                                        dbc.Input(id="proc-internamientos-durante-cant", type="number", min=0, className="mb-2"),
                                    ])
                                ]),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Canalizar a Psiquiatría"),
                                        dbc.Select(id="proc-canalizacion-psiquiatria", options=[
                                            {"label": "Sí", "value": "true"},
                                            {"label": "No", "value": "false"}
                                        ], placeholder="Selecciona...", className="mb-2"),
                                    ]),
                                    dbc.Col([
                                        dbc.Label("Fecha Canalización"),
                                        dbc.Input(id="proc-fecha-canalizacion", type="date", className="mb-2"),
                                    ])
                                ]),
                                
                                html.Div([
                                    dbc.Label("DX Psiquiatría"),
                                    dbc.Input(id="proc-dx-psiquiatria", type="text", placeholder="DX Psiquiatría...", className="mb-2"),
                                ], id="div-proc-psiquiatria", style={"display": "none"}),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Canalizar otra disciplina"),
                                        dbc.Select(id="proc-canalizacion-otra", options=[
                                            {"label": "Sí", "value": "true"},
                                            {"label": "No", "value": "false"}
                                        ], placeholder="Selecciona...", className="mb-2"),
                                    ]),
                                    dbc.Col([
                                        dbc.Label("¿Cuál disciplina?"),
                                        dbc.Input(id="proc-canalizacion-otra-cual", type="text", placeholder="Anotar disciplina...", className="mb-2"),
                                    ])
                                ]),
                                
                                dbc.Label("Referido a terapeuta externo colaborador"),
                                dbc.Select(id="proc-referido-externo", options=[
                                    {"label": "Sí", "value": "true"},
                                    {"label": "No", "value": "false"}
                                ], placeholder="Selecciona...", className="mb-2"),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Espora Comunitaria"),
                                        dbc.Select(id="proc-intervencion-espora-comunitaria", options=[
                                            {"label": "Sí", "value": "true"},
                                            {"label": "No", "value": "false"}
                                        ], placeholder="Selecciona...", className="mb-2"),
                                    ]),
                                    dbc.Col([
                                        dbc.Label("¿En qué consistió?"),
                                        dbc.Textarea(id="proc-intervencion-espora-comunitaria-cual", rows=1, placeholder="Detalles de intervención...", className="mb-2"),
                                    ])
                                ]),
                            ], width=12, md=4),
                        ]),
                        
                        dbc.Button("💾 Guardar Control de Proceso", id="btn-save-process-data", color="success", className="mt-3 float-end"),
                        dbc.Alert(id="process-data-alert", is_open=False, color="success", className="mt-3 w-50")
                    ])
                ], className="mb-4 shadow-sm border-0 glass-card")
            ], width=12)
        ]),
        
        # Modal para Agendar (Original)
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Programar Nueva Sesión")),
            dbc.ModalBody([
                dbc.Label("Fecha y Hora"),
                dbc.Input(id="new-session-date", type="datetime-local", className="mb-3"),
                dbc.Label("Modalidad"),
                dbc.Select(id="new-session-modality", options=[
                    {"label": "En Línea", "value": "online"},
                    {"label": "Presencial", "value": "in_person"}
                ]),
                dbc.Alert(id="new-session-alert", is_open=False, color="danger", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-cancel-schedule", className="ms-auto"),
                dbc.Button("Programar", id="btn-submit-schedule", color="primary")
            ])
        ], id="schedule-patient-modal", is_open=False),
        
        # Modal para Nueva Captura Clínica (Con notas libres y carga de archivos)
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Llenar Nuevo Cuestionario / Captura Clínica")),
            dbc.ModalBody([
                dbc.Label("Seleccionar Plantilla:"),
                dcc.Dropdown(id="template-dropdown", className="mb-3"),
                html.Hr(),
                dcc.Loading(html.Div(id="template-fields-container")),
                
                html.Hr(),
                html.H6("Notas Libres y Archivos Adjuntos (Digitalización)", className="text-primary fw-bold mb-2"),
                dbc.Label("Nota Clínica Escrita / Libre"),
                dbc.Textarea(id="submission-free-notes", placeholder="Escribe aquí notas clínicas libres o comentarios adicionales sobre este registro (ej. observaciones o resumen si no usas plantilla)...", rows=4, className="mb-3"),
                
                dbc.Label("Adjuntar Nota Escaneada, Foto o Archivo de Texto"),
                dcc.Upload(
                    id="submission-upload",
                    children=html.Div([
                        "Arrastra y suelta o selecciona un archivo (Imágenes, PDF, Notas de Texto)"
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'marginBottom': '10px',
                        'cursor': 'pointer'
                    },
                    multiple=False
                ),
                html.Div(id="submission-upload-preview", className="mb-3 text-muted small"),
                dcc.Store(id="submission-upload-store", data=None),
                
                dbc.Alert(id="new-submission-alert", is_open=False, color="success", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cerrar", id="btn-cancel-submission", className="ms-auto", color="secondary"),
                dbc.Button("Guardar Evaluación", id="btn-submit-submission", color="primary")
            ])
        ], id="new-submission-modal", is_open=False, size="lg"),
        
        # Modal para Editar Notas Clínicas y Problemáticas de Evolución
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Editar Evolución y Problemáticas de la Sesión")),
            dbc.ModalBody([
                dbc.Input(id="edit-session-id", type="hidden"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Modalidad"),
                        dbc.Select(id="edit-session-modality", options=[
                            {"label": "En Línea", "value": "online"},
                            {"label": "Presencial", "value": "in_person"}
                        ], className="mb-3"),
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Estado de la Cita"),
                        dbc.Select(id="edit-session-status", options=[
                            {"label": "Programada", "value": "scheduled"},
                            {"label": "Completada", "value": "completed"},
                            {"label": "Cancelada", "value": "cancelled"}
                        ], className="mb-3"),
                    ], width=6)
                ]),
                dbc.Label("Notas de Evolución Clínica / Notas Clínicas"),
                dbc.Textarea(id="edit-session-notes", rows=4, placeholder="Escribe aquí las notas clínicas de evolución de esta sesión...", className="mb-3"),
                
                html.Hr(),
                html.H6("Problemáticas Trabajadas en esta Sesión (Ausencia/Presencia)", className="text-primary fw-bold mb-3"),
                
                dbc.Row([
                    # Col 1: Checklist of simpler problematics
                    dbc.Col([
                        dbc.Label("Generales (Marca las que apliquen):", className="text-muted small fw-bold"),
                        dcc.Checklist(
                            id="edit-issues-simple",
                            options=[
                                {"label": "Tristeza", "value": "TRISTEZA"},
                                {"label": "Vacío", "value": "VACÍO"},
                                {"label": "Soledad", "value": "SOLEDAD"},
                                {"label": "Desesperanza", "value": "DESESPERANZA"},
                                {"label": "Ansiedad", "value": "ANSIEDAD"},
                                {"label": "Problemas Familiares", "value": "PROBLEMAS FAMILIARES"},
                                {"label": "Problemas Académicos", "value": "PROBLEMAS ACADÉMICOS"},
                                {"label": "Problemas de Pareja", "value": "PROBLEMAS DE PAREJA"},
                                {"label": "Problemas Autoestima / Imagen", "value": "PROBLEMAS AUTOESTIMA/ IMAGEN"},
                                {"label": "Problemas Relación Pares", "value": "PROBLEMAS PARA RELACIONARSE CON PARES"},
                                {"label": "Proyecto de Vida", "value": "PROYECTO DE VIDA"},
                                {"label": "Pérdidas / Duelos", "value": "PÉRDIDAS / DUELOS"},
                                {"label": "Identidad Sexual / Género", "value": "IDENTIDAD SEXUAL/GÉNERO"},
                                {"label": "Autolesiones", "value": "AUTOLESIONES"},
                                {"label": "Alucinaciones", "value": "ALUCINACIONES"}
                            ],
                            value=[],
                            labelStyle={"display": "block", "marginBottom": "5px"},
                            inputStyle={"marginRight": "8px"}
                        )
                    ], width=6),
                    
                    # Col 2: Checkboxes with conditional inputs
                    dbc.Col([
                        dbc.Label("Específicas (Requieren mayor detalle):", className="text-muted small fw-bold"),
                        
                        # Trastornos Alimentación
                        dbc.Checkbox(id="edit-issue-alimentacion", label="Trastornos en la alimentación", className="mb-1"),
                        html.Div(dbc.Input(id="edit-issue-alimentacion-desc", placeholder="Especifica cuál...", size="sm", className="mb-2"), id="div-issue-alimentacion", style={"display": "none"}, className="ms-4"),
                        
                        # Violencia Intrafamiliar
                        dbc.Checkbox(id="edit-issue-violencia-intra", label="Violencia intrafamiliar", className="mb-1"),
                        html.Div(dbc.Textarea(id="edit-issue-violencia-intra-desc", placeholder="Describir brevemente la situación...", size="sm", rows=2, className="mb-2"), id="div-issue-violencia-intra", style={"display": "none"}, className="ms-4"),
                        
                        # Violencia Género
                        dbc.Checkbox(id="edit-issue-violencia-genero", label="Violencia de género", className="mb-1"),
                        html.Div(dbc.Textarea(id="edit-issue-violencia-genero-desc", placeholder="Describir brevemente la situación...", size="sm", rows=2, className="mb-2"), id="div-issue-violencia-genero", style={"display": "none"}, className="ms-4"),
                        
                        # Violencia Pareja
                        dbc.Checkbox(id="edit-issue-violencia-pareja", label="Violencia de pareja", className="mb-1"),
                        html.Div(dbc.Textarea(id="edit-issue-violencia-pareja-desc", placeholder="Describir brevemente la situación...", size="sm", rows=2, className="mb-2"), id="div-issue-violencia-pareja", style={"display": "none"}, className="ms-4"),
                        
                        # Violencia Temas Criminales
                        dbc.Checkbox(id="edit-issue-violencia-criminal", label="Violencia por temas criminales", className="mb-1"),
                        html.Div(dbc.Textarea(id="edit-issue-violencia-criminal-desc", placeholder="Describir brevemente la situación...", size="sm", rows=2, className="mb-2"), id="div-issue-violencia-criminal", style={"display": "none"}, className="ms-4"),
                        
                        # Violencia Sexual
                        dbc.Checkbox(id="edit-issue-violencia-sexual", label="Violencia sexual", className="mb-1"),
                        html.Div(dbc.Textarea(id="edit-issue-violencia-sexual-desc", placeholder="Describir brevemente la situación...", size="sm", rows=2, className="mb-2"), id="div-issue-violencia-sexual", style={"display": "none"}, className="ms-4"),
                        
                        # Disidencias
                        dbc.Checkbox(id="edit-issue-disidencias", label="Pertenece a disidencias", className="mb-1"),
                        html.Div(dbc.Input(id="edit-issue-disidencias-desc", placeholder="Especifica cuál...", size="sm", className="mb-2"), id="div-issue-disidencias", style={"display": "none"}, className="ms-4"),
                        
                        # Discapacidad
                        dbc.Checkbox(id="edit-issue-discapacidad", label="Discapacidad", className="mb-1"),
                        html.Div(dbc.Input(id="edit-issue-discapacidad-desc", placeholder="Especifica cuál...", size="sm", className="mb-2"), id="div-issue-discapacidad", style={"display": "none"}, className="ms-4"),
                        
                        # Consumo Sustancias
                        dbc.Checkbox(id="edit-issue-consumo", label="Consumo problemático de sustancias", className="mb-1"),
                        html.Div([
                            dcc.Checklist(
                                id="edit-issue-consumo-list",
                                options=[
                                    {"label": "Alcohol", "value": "alcohol"},
                                    {"label": "Marihuana", "value": "marihuana"},
                                    {"label": "Opioides o Heroína", "value": "opioides o heroína"},
                                    {"label": "Solventes", "value": "solventes"},
                                    {"label": "Cristal", "value": "cristal"}
                                ],
                                value=[],
                                labelStyle={"display": "block", "marginBottom": "2px"},
                                inputStyle={"marginRight": "5px"},
                                className="text-muted small"
                            ),
                            dbc.Input(id="edit-issue-consumo-otro", placeholder="Otro consumo...", size="sm", className="mt-1")
                        ], id="div-issue-consumo", style={"display": "none"}, className="ms-4 mb-2"),
                        
                        # Enfermedades Físicas
                        dbc.Checkbox(id="edit-issue-enfermedades", label="Enfermedades físicas", className="mb-1"),
                        html.Div(dbc.Input(id="edit-issue-enfermedades-desc", placeholder="Especifica cuál es la situación...", size="sm", className="mb-2"), id="div-issue-enfermedades", style={"display": "none"}, className="ms-4")
                        
                    ], width=6)
                ]),
                
                html.Hr(),
                html.H6("Ideación Suicida e Intentos (Severidad)", className="text-danger fw-bold mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Ideación Suicida (Inicio Tratamiento)", className="small text-muted"),
                        dbc.Select(id="edit-issue-suicidio-inicio", options=[
                            {"label": "Ausente", "value": "Ausente"},
                            {"label": "Presente", "value": "Presente"}
                        ], value="Ausente", className="mb-2")
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Ideación Suicida (Fin Tratamiento)", className="small text-muted"),
                        dbc.Select(id="edit-issue-suicidio-fin", options=[
                            {"label": "Ausente", "value": "Ausente"},
                            {"label": "Presente", "value": "Presente"}
                        ], value="Ausente", className="mb-2")
                    ], width=6)
                ]),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Intentos suicidas PREVIOS", className="small text-muted"),
                        dbc.Input(id="edit-issue-intentos-previos", type="number", min=0, step=1, className="mb-2")
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Intentos suicidas DURANTE el tratamiento", className="small text-muted"),
                        dbc.Input(id="edit-issue-intentos-durante", type="number", min=0, step=1, className="mb-2")
                    ], width=6)
                ]),
                
                dbc.Alert(id="edit-session-alert", is_open=False, color="danger", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-cancel-edit-session", className="ms-auto", color="secondary"),
                dbc.Button("Guardar Cambios de Sesión", id="btn-submit-edit-session", color="primary")
            ])
        ], id="edit-session-modal", is_open=False, size="lg"),
        
        # Modal para Enviar Correo al Consultante
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("✉️ Enviar Correo al Consultante")),
            dbc.ModalBody([
                dbc.Label("Tipo de Correo:", className="fw-bold"),
                dbc.RadioItems(
                    id="email-template-type",
                    options=[
                        {"label": "📅 Recordar Próxima Cita", "value": "appointment"},
                        {"label": "📋 Enviar Formulario / Cuestionario", "value": "form"},
                        {"label": "✏️ En Blanco (Libre)", "value": "blank"}
                    ],
                    value="appointment",
                    inline=True,
                    className="mb-3 text-primary"
                ),
                
                html.Div([
                    dbc.Label("Seleccionar Formulario / Cuestionario:"),
                    dcc.Dropdown(
                        id="email-form-select",
                        placeholder="Selecciona una plantilla de cuestionario...",
                        className="mb-3"
                    )
                ], id="div-email-form-select", style={"display": "none"}),
                
                dbc.Label("Correo Destinatario:"),
                dbc.Input(id="email-recipient-input", type="email", placeholder="correo@ejemplo.com", className="mb-3"),
                
                dbc.Label("Asunto del Correo:"),
                dbc.Input(id="email-subject-input", type="text", placeholder="Escribe el asunto...", className="mb-3"),
                
                dbc.Label("Cuerpo del Mensaje (Editable):"),
                dbc.Textarea(id="email-body-textarea", rows=8, placeholder="Escribe o modifica aquí el cuerpo del correo...", className="mb-3"),
                
                dbc.Alert(id="email-send-alert", is_open=False, color="success", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-cancel-email-modal", className="ms-auto", color="secondary"),
                dbc.Button("📤 Enviar Correo", id="btn-send-email-submit", color="success")
            ])
        ], id="email-patient-modal", is_open=False, size="lg")
    ], fluid=True, className="py-4")

# Callbacks

@callback(
    Output("refer-api-alert", "children"),
    Output("refer-api-alert", "color"),
    Output("refer-api-alert", "is_open"),
    Input("btn-refer-api", "n_clicks"),
    State("current-case-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def handle_refer_from_api(n_clicks, case_id, token):
    if not n_clicks or not case_id or not token:
        return no_update, no_update, False
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(f"{API_URL}/cases/{case_id}/refer_from_api", headers=headers)
        if res.status_code == 200:
            return "✅ Alumno migrado exitosamente a la Lista de Espera de la sede con etiqueta '🚨 Derivado de API' y toda la información clínica de su perfil.", "success", True
        detail = res.json().get("detail", res.text)
        return f"Error al derivar a Lista de Espera: {detail}", "danger", True
    except Exception as e:
        return f"Error de conexión: {str(e)}", "danger", True


@callback(
    Output("patient-title", "children"),
    Output("patient-info-content", "children"),
    Output("sessions-timeline-container", "children"),
    Input("current-case-id", "data"),
    Input("schedule-patient-modal", "is_open"), 
    Input("edit-session-modal", "is_open"),
    State("auth-token", "data")
)
def load_patient_data(case_id, modal_open, edit_modal_open, token):
    if not token or not case_id:
        return dash.no_update, dash.no_update, dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/cases", headers=headers)
        if res.status_code == 200:
            cases = res.json()
            case_data = next((c for c in cases if str(c['id']) == str(case_id)), None)
            
            if case_data:
                p = case_data['participant']
                title = f"Expediente Clínico: {p['full_name']}"
                
                status_map = {"waiting": "Lista de Espera", "assigned": "Asignado", "active": "Activo", "closed": "Cerrado"}
                
                info = [
                    html.P([html.Strong("Folio Anónimo: "), dbc.Badge(p.get('anonymous_folio', 'N/D'), color="dark")]),
                    html.P([html.Strong("No. Cuenta: "), p.get('student_account')]),
                    html.P([html.Strong("Email: "), p.get('email')]),
                    html.P([html.Strong("Facultad: "), p.get('faculty', 'N/D')]),
                    html.P([html.Strong("Estado del Caso: "), dbc.Badge(status_map.get(case_data['status'], case_data['status']), color="info")]),
                ]
                
                sessions = case_data.get('sessions', [])
                sessions = sorted(sessions, key=lambda x: x['session_date'], reverse=True)
                timeline_ui = []
                for s in sessions:
                    try:
                        dt = datetime.fromisoformat(s['session_date'].replace('Z', '+00:00'))
                        parsed_date = dt.strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        parsed_date = s['session_date']
                    
                    status = s.get('status', 'scheduled')
                    notes = s.get('therapist_notes', 'Sin notas capturadas.') or 'Sin notas capturadas.'
                    
                    # Format worked issues summary
                    issues_formatted = ""
                    worked_dict = s.get("worked_issues")
                    if worked_dict:
                        issues_list = []
                        for k, v in worked_dict.items():
                            if v:
                                if isinstance(v, bool):
                                    issues_list.append(k)
                                elif isinstance(v, dict):
                                    if v.get("checked"):
                                        detail = v.get("detail") or v.get("specify") or v.get("description") or ""
                                        if detail:
                                            issues_list.append(f"{k} ({detail})")
                                        else:
                                            issues_list.append(k)
                                else:
                                    issues_list.append(f"{k}: {v}")
                        if issues_list:
                            issues_formatted = ", ".join(issues_list)
                            
                    bg_color = "primary" if status == "scheduled" else "success" if status == "completed" else "danger"
                    
                    card = dbc.Card([
                        dbc.CardHeader([
                            html.Strong(f"Estado de la Cita: {status.upper()}"),
                            html.Span(f" - {parsed_date}", className="text-muted float-end pb-1"),
                            dbc.Button("📝 Editar Evolución", id={"type": "btn-edit-session", "index": s['id']}, size="sm", color="link", className="float-end p-0 me-3")
                        ]),
                        dbc.CardBody([
                            html.P(notes, className="mb-0 small"),
                            html.Div([
                                html.Small([
                                    html.Strong("Problemáticas abordadas: "),
                                    html.Span(issues_formatted, className="text-muted")
                                ], className="d-block mt-2 pt-2 border-top")
                            ] if issues_formatted else [])
                        ])
                    ], color=bg_color, outline=True, className="mb-3")
                    timeline_ui.append(card)
                    
                if not timeline_ui:
                    timeline_ui = [html.P("El paciente aún no cuenta con historial de sesiones clínicas programadas en su expediente.", className="text-muted small")]
                
                return title, info, timeline_ui
    except Exception as e:
        print(f"Error loading patient data: {e}")
        
    return "Error cargando paciente", html.P("No se pudo cargar la información.", className="text-danger"), []

@callback(
    Output("patient-ls-sync-alert", "children"),
    Output("patient-ls-sync-alert", "color"),
    Output("patient-ls-sync-alert", "is_open"),
    Output("patient-ls-sync-trigger", "data"),
    Input("btn-sync-patient-ls", "n_clicks"),
    State("patient-ls-sync-trigger", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def handle_patient_ls_sync(n_clicks, current_trigger, token):
    if not n_clicks or not token:
        return no_update, no_update, no_update, no_update
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(f"{API_URL}/limesurvey/sync", headers=headers, timeout=25)
        if res.status_code == 200:
            report = res.json().get("report", {})
            f_subs = report.get("followup_submissions", 0)
            return f"✓ Sincronización con LimeSurvey completada ({f_subs} cuestionarios de seguimiento nuevos).", "success", True, (current_trigger or 0) + 1
        return f"Error al sincronizar: {res.text}", "warning", True, no_update
    except Exception as e:
        return f"Error de conexión con LimeSurvey: {str(e)}", "danger", True, no_update

@callback(
    Output("submissions-timeline-container", "children"),
    Input("current-case-id", "data"),
    Input("new-submission-modal", "is_open"), # Refresh after saving
    Input("quick-submission-alert", "is_open"), # Refresh after saving quick submission
    Input("patient-ls-sync-trigger", "data"),
    Input("auth-token", "data")
)
def load_submissions(case_id, modal_open, quick_alert_open, ls_sync_trigger, token):
    if not token or not case_id:
        return dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/fields/submissions/case/{case_id}", headers=headers)
        if res.status_code == 200:
            submissions = res.json()
            if not submissions:
                return html.P("No hay evaluaciones registradas.", className="text-muted small")
                
            submissions = sorted(submissions, key=lambda x: x['submitted_at'], reverse=True)
            
            cards = []
            for sub in submissions:
                template_name = sub.get("template", {}).get("name", "Formulario Desconocido")
                date_str = sub.get("submitted_at", "")[:10]
                
                fields_ui = []
                for val in sub.get("field_values", []):
                    f_name = val.get("field", {}).get("label", val.get("form_field_id"))
                    f_val = val.get("value_text", "")
                    fields_ui.append(html.Div([
                        html.Strong(f"{f_name}: ", className="small"),
                        html.Span(f_val, className="small text-muted")
                     ]))
                
                attachments = sub.get("attachments", [])
                attachments_ui = []
                for att in attachments:
                    fname = att.get("filename", "archivo")
                    ctype = att.get("content_type", "")
                    fdata = att.get("file_data", "")
                    
                    if "text/plain" in ctype or fname.endswith(".txt"):
                        try:
                            import base64
                            decoded_text = base64.b64decode(fdata.encode("utf-8")).decode("utf-8")
                        except Exception:
                            decoded_text = "[Error al decodificar texto]"
                        attachments_ui.append(html.Div([
                            html.Strong("📝 Nota Escrita:", className="small text-primary d-block mt-2"),
                            html.Blockquote(decoded_text, style={
                                "borderLeft": "3px solid #007bff",
                                "paddingLeft": "10px",
                                "backgroundColor": "#f8f9fa",
                                "fontStyle": "italic",
                                "whiteSpace": "pre-wrap"
                            }, className="small p-2 rounded mb-2")
                        ]))
                    elif "image/" in ctype or fname.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                        image_src = f"data:{ctype};base64,{fdata}"
                        attachments_ui.append(html.Div([
                            html.Strong(f"📷 Imagen Adjunta: {fname}", className="small text-success d-block mt-2"),
                            html.A([
                                html.Img(src=image_src, style={"maxHeight": "150px", "maxWidth": "100%", "cursor": "pointer"}, className="rounded border mt-1 img-thumbnail")
                            ], href=image_src, target="_blank")
                        ], className="mb-2"))
                    else:
                        download_src = f"data:{ctype};base64,{fdata}"
                        attachments_ui.append(html.Div([
                            html.A(f"📎 Descargar {fname}", href=download_src, download=fname, className="btn btn-outline-secondary btn-sm mt-2 d-inline-block")
                        ], className="mb-2"))
                
                cards.append(dbc.Card([
                    dbc.CardHeader(html.Strong(f"{template_name} ({date_str})")),
                    dbc.CardBody(fields_ui + attachments_ui)
                ], className="mb-3 border-left-primary shadow-sm"))
                
            return cards
    except Exception as e:
        print("Error loading submissions:", e)
    return html.P("Error cargando evaluaciones.", className="text-danger small")

@callback(
    Output("new-submission-modal", "is_open"),
    Output("template-dropdown", "options"),
    Output("submission-free-notes", "value"),
    Output("submission-upload-store", "data"),
    Output("submission-upload-preview", "children"),
    Input("btn-new-submission", "n_clicks"),
    Input("btn-cancel-submission", "n_clicks"),
    State("new-submission-modal", "is_open"),
    State("auth-token", "data")
)
def toggle_submission_modal(n_open, n_close, is_open, token):
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-cancel-submission":
        return False, dash.no_update, "", None, ""
        
    if trigger_id == "btn-new-submission":
        headers = {"Authorization": f"Bearer {token}"}
        try:
            res = requests.get(f"{API_URL}/fields/templates", headers=headers)
            opts = [{"label": t["name"], "value": t["id"]} for t in res.json()]
            return True, opts, "", None, ""
        except:
            return True, [], "", None, ""
    return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    Output("template-fields-container", "children"),
    Input("template-dropdown", "value"),
    State("auth-token", "data")
)
def load_template_fields(template_id, token):
    if not template_id: return []
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/fields/templates/{template_id}/fields", headers=headers)
        fields = res.json()
        
        inputs = []
        for f in fields:
            inputs.append(html.Div([
                dbc.Label(f["label"], className="small fw-bold text-muted"),
                dbc.Input(id={"type": "new-submission-input", "field_id": f["id"]}, type="text", className="mb-3")
            ]))
        return inputs
    except:
        return html.P("Error cargando campos.")

@callback(
    Output("new-submission-alert", "children"),
    Output("new-submission-alert", "is_open"),
    Output("new-submission-alert", "color"),
    Input("btn-submit-submission", "n_clicks"),
    State("template-dropdown", "value"),
    State({"type": "new-submission-input", "field_id": dash.ALL}, "value"),
    State({"type": "new-submission-input", "field_id": dash.ALL}, "id"),
    State("submission-free-notes", "value"),
    State("submission-upload-store", "data"),
    State("current-case-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_new_submission(n_clicks, template_id, values, ids, free_notes_val, upload_data, case_id, token):
    if not n_clicks or not template_id: return dash.no_update, dash.no_update, dash.no_update
    headers = {"Authorization": f"Bearer {token}"}
    
    fields_payload = []
    for val, id_dict in zip(values, ids):
        if val is not None and str(val).strip():
            fields_payload.append({
                "form_field_id": id_dict["field_id"],
                "value_text": str(val)
            })
            
    attachments_payload = []
    
    # Handle manual free notes as a text file attachment
    if free_notes_val and free_notes_val.strip():
        import base64
        encoded_note = base64.b64encode(free_notes_val.encode("utf-8")).decode("utf-8")
        attachments_payload.append({
            "filename": "nota_libre.txt",
            "content_type": "text/plain",
            "file_data": encoded_note
        })
        
    # Handle uploaded file attachment
    if upload_data:
        attachments_payload.append(upload_data)
        
    payload = {
        "form_template_id": template_id,
        "case_id": int(case_id),
        "fields": fields_payload,
        "attachments": attachments_payload
    }
    try:
        res = requests.post(f"{API_URL}/fields/submissions", json=payload, headers=headers)
        if res.status_code == 200:
            return "Guardado exitoso.", True, "success"
        else:
            return f"Error: {res.text}", True, "danger"
    except Exception as e:
        return str(e), True, "danger"

@callback(
    Output("submission-upload-store", "data", allow_duplicate=True),
    Output("submission-upload-preview", "children", allow_duplicate=True),
    Input("submission-upload", "contents"),
    State("submission-upload", "filename"),
    prevent_initial_call=True
)
def handle_file_upload(contents, filename):
    if not contents:
        return None, ""
    try:
        header, base64_data = contents.split(",", 1)
        content_type = header.split(";")[0].replace("data:", "")
        preview = f"✓ Archivo cargado: {filename} ({content_type})"
        store_data = {
            "filename": filename,
            "content_type": content_type,
            "file_data": base64_data
        }
        return store_data, preview
    except Exception as e:
        return None, f"Error al procesar el archivo: {str(e)}"

@callback(
    Output("schedule-patient-modal", "is_open", allow_duplicate=True),
    [Input("btn-open-schedule", "n_clicks"), Input("btn-cancel-schedule", "n_clicks"), Input("btn-submit-schedule", "n_clicks")],
    [State("schedule-patient-modal", "is_open"), State("new-session-date", "value"), State("new-session-modality", "value"), State("current-case-id", "data"), State("auth-token", "data")],
    prevent_initial_call=True
)
def handle_schedule_modal(n_open, n_cancel, n_submit, is_open, date_val, modality, case_id, token):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-open-schedule": return True
    elif trigger_id == "btn-cancel-schedule": return False
    elif trigger_id == "btn-submit-schedule" and date_val and modality:
        headers = {"Authorization": f"Bearer {token}"}
        dt = datetime.fromisoformat(date_val).isoformat() + "Z"
        try:
            requests.post(f"{API_URL}/cases/{case_id}/sessions", json={"case_id": int(case_id), "session_date": dt, "modality": modality}, headers=headers)
            return False
        except:
            pass
    return is_open

# --- Session Edit Modal Callbacks ---

# Visibility toggles for session details
@callback(
    Output("div-issue-alimentacion", "style"),
    Output("div-issue-violencia-intra", "style"),
    Output("div-issue-violencia-genero", "style"),
    Output("div-issue-violencia-pareja", "style"),
    Output("div-issue-violencia-criminal", "style"),
    Output("div-issue-violencia-sexual", "style"),
    Output("div-issue-disidencias", "style"),
    Output("div-issue-discapacidad", "style"),
    Output("div-issue-consumo", "style"),
    Output("div-issue-enfermedades", "style"),
    Input("edit-issue-alimentacion", "value"),
    Input("edit-issue-violencia-intra", "value"),
    Input("edit-issue-violencia-genero", "value"),
    Input("edit-issue-violencia-pareja", "value"),
    Input("edit-issue-violencia-criminal", "value"),
    Input("edit-issue-violencia-sexual", "value"),
    Input("edit-issue-disidencias", "value"),
    Input("edit-issue-discapacidad", "value"),
    Input("edit-issue-consumo", "value"),
    Input("edit-issue-enfermedades", "value")
)
def toggle_session_details(alimentacion, intra, genero, pareja, criminal, sexual, disidencias, discapacidad, consumo, enfermedades):
    d_block = {"display": "block"}
    d_none = {"display": "none"}
    return (
        d_block if alimentacion else d_none,
        d_block if intra else d_none,
        d_block if genero else d_none,
        d_block if pareja else d_none,
        d_block if criminal else d_none,
        d_block if sexual else d_none,
        d_block if disidencias else d_none,
        d_block if discapacidad else d_none,
        d_block if consumo else d_none,
        d_block if enfermedades else d_none
    )

# Load session to modal
@callback(
    Output("edit-session-modal", "is_open"),
    Output("edit-session-id", "value"),
    Output("edit-session-notes", "value"),
    Output("edit-session-modality", "value"),
    Output("edit-session-status", "value"),
    Output("edit-issues-simple", "value"),
    Output("edit-issue-alimentacion", "value"),
    Output("edit-issue-alimentacion-desc", "value"),
    Output("edit-issue-violencia-intra", "value"),
    Output("edit-issue-violencia-intra-desc", "value"),
    Output("edit-issue-violencia-genero", "value"),
    Output("edit-issue-violencia-genero-desc", "value"),
    Output("edit-issue-violencia-pareja", "value"),
    Output("edit-issue-violencia-pareja-desc", "value"),
    Output("edit-issue-violencia-criminal", "value"),
    Output("edit-issue-violencia-criminal-desc", "value"),
    Output("edit-issue-violencia-sexual", "value"),
    Output("edit-issue-violencia-sexual-desc", "value"),
    Output("edit-issue-disidencias", "value"),
    Output("edit-issue-disidencias-desc", "value"),
    Output("edit-issue-discapacidad", "value"),
    Output("edit-issue-discapacidad-desc", "value"),
    Output("edit-issue-consumo", "value"),
    Output("edit-issue-consumo-list", "value"),
    Output("edit-issue-consumo-otro", "value"),
    Output("edit-issue-enfermedades", "value"),
    Output("edit-issue-enfermedades-desc", "value"),
    Output("edit-issue-suicidio-inicio", "value"),
    Output("edit-issue-suicidio-fin", "value"),
    Output("edit-issue-intentos-previos", "value"),
    Output("edit-issue-intentos-durante", "value"),
    Input({"type": "btn-edit-session", "index": dash.ALL}, "n_clicks"),
    Input("btn-cancel-edit-session", "n_clicks"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def load_session_details(btn_clicks, cancel_click, token):
    ctx = dash.callback_context
    if not ctx.triggered or not token:
        return dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    trigger_val = ctx.triggered[0].get("value")
    
    # Ignore initial triggers or dynamic mountings without actual clicks
    if isinstance(trigger_val, list):
        if not trigger_val or all(v is None or v == 0 for v in trigger_val):
            return dash.no_update
    elif trigger_val is None or trigger_val == 0:
        return dash.no_update
        
    # Check if we clicked cancel
    if trigger_id == "btn-cancel-edit-session":
        return (False, "", "", "online", "scheduled", [], 
                False, "", False, "", False, "", False, "", False, "", False, "", 
                False, "", False, "", False, [], "", False, "", "Ausente", "Ausente", 0, 0)
                
    # Otherwise, we clicked a session edit button
    try:
        trigger_dict = eval(trigger_id)
        session_id = trigger_dict["index"]
    except:
        return dash.no_update
        
    # Fetch session from backend
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{API_URL}/sessions/{session_id}", headers=headers)
    if res.status_code != 200:
        return dash.no_update
        
    s = res.json()
    notes = s.get("therapist_notes") or ""
    modality = s.get("modality") or "online"
    status = s.get("status") or "scheduled"
    
    worked_dict = s.get("worked_issues") or {}
    
    # Process simple list
    simple_list = []
    for issue in ["TRISTEZA", "VACÍO", "SOLEDAD", "DESESPERANZA", "ANSIEDAD", "PROBLEMAS FAMILIARES", "PROBLEMAS ACADÉMICOS", "PROBLEMAS DE PAREJA", "PROBLEMAS AUTOESTIMA/ IMAGEN", "PROBLEMAS PARA RELACIONARSE CON PARES", "PROYECTO DE VIDA", "PÉRDIDAS / DUELOS", "IDENTIDAD SEXUAL/GÉNERO", "AUTOLESIONES", "ALUCINACIONES"]:
        if worked_dict.get(issue) is True:
            simple_list.append(issue)
            
    # Process complex dictionaries
    def get_complex(key):
        v = worked_dict.get(key)
        if isinstance(v, dict):
            return v.get("checked", False), v.get("specify") or v.get("description") or v.get("detail") or ""
        elif isinstance(v, bool):
            return v, ""
        return False, ""
        
    alim_chk, alim_desc = get_complex("TRASTORNOS EN LA ALIMENTACIÓN")
    v_intra_chk, v_intra_desc = get_complex("VIOLENCIA INTRAFAMILIAR")
    v_gen_chk, v_gen_desc = get_complex("VIOLENCIA DE GÉNERO")
    v_par_chk, v_par_desc = get_complex("VIOLENCIA DE PAREJA")
    v_crim_chk, v_crim_desc = get_complex("VIOLENCIA POR TEMAS CRIMINALES")
    v_sex_chk, v_sex_desc = get_complex("VIOLENCIA SEXUAL")
    disid_chk, disid_desc = get_complex("PERTENECE A LAS DISIDENCIAS")
    disc_chk, disc_desc = get_complex("DISCAPACIDAD")
    enfer_chk, enfer_desc = get_complex("ENFERMEDADES FÍSICAS")
    
    # Consumo sustancias
    consumo_val = worked_dict.get("CONSUMO PROBLEMÁTICO DE SUSTANCIAS")
    consumo_chk = False
    consumo_list = []
    consumo_otro = ""
    if isinstance(consumo_val, dict):
        consumo_chk = consumo_val.get("checked", False)
        consumo_list = consumo_val.get("substances") or []
        consumo_otro = consumo_val.get("otro") or ""
    elif isinstance(consumo_val, bool):
        consumo_chk = consumo_val
        
    # Suicidio
    suicidio_inicio = worked_dict.get("IDEACIÓN SUICIDA al iniciar el tratamiento") or "Ausente"
    suicidio_fin = worked_dict.get("IDEACIÓN SUICIDA al finalizar el tratamiento") or "Ausente"
    intentos_previos = worked_dict.get("INTENTOS SUICIDAS PREVIOS ¿cuántos?") or 0
    intentos_durante = worked_dict.get("INTENTOS SUICIDAS DURANTE EL TRATAMIENTO ¿cuántos?") or 0
    
    return (
        True, session_id, notes, modality, status, simple_list,
        alim_chk, alim_desc,
        v_intra_chk, v_intra_desc,
        v_gen_chk, v_gen_desc,
        v_par_chk, v_par_desc,
        v_crim_chk, v_crim_desc,
        v_sex_chk, v_sex_desc,
        disid_chk, disid_desc,
        disc_chk, disc_desc,
        consumo_chk, consumo_list, consumo_otro,
        enfer_chk, enfer_desc,
        suicidio_inicio, suicidio_fin, intentos_previos, intentos_durante
    )

# Save session evolution
@callback(
    Output("edit-session-alert", "children"),
    Output("edit-session-alert", "is_open"),
    Output("edit-session-modal", "is_open", allow_duplicate=True),
    Input("btn-submit-edit-session", "n_clicks"),
    State("edit-session-id", "value"),
    State("edit-session-notes", "value"),
    State("edit-session-modality", "value"),
    State("edit-session-status", "value"),
    State("edit-issues-simple", "value"),
    State("edit-issue-alimentacion", "value"),
    State("edit-issue-alimentacion-desc", "value"),
    State("edit-issue-violencia-intra", "value"),
    State("edit-issue-violencia-intra-desc", "value"),
    State("edit-issue-violencia-genero", "value"),
    State("edit-issue-violencia-genero-desc", "value"),
    State("edit-issue-violencia-pareja", "value"),
    State("edit-issue-violencia-pareja-desc", "value"),
    State("edit-issue-violencia-criminal", "value"),
    State("edit-issue-violencia-criminal-desc", "value"),
    State("edit-issue-violencia-sexual", "value"),
    State("edit-issue-violencia-sexual-desc", "value"),
    State("edit-issue-disidencias", "value"),
    State("edit-issue-disidencias-desc", "value"),
    State("edit-issue-discapacidad", "value"),
    State("edit-issue-discapacidad-desc", "value"),
    State("edit-issue-consumo", "value"),
    State("edit-issue-consumo-list", "value"),
    State("edit-issue-consumo-otro", "value"),
    State("edit-issue-enfermedades", "value"),
    State("edit-issue-enfermedades-desc", "value"),
    State("edit-issue-suicidio-inicio", "value"),
    State("edit-issue-suicidio-fin", "value"),
    State("edit-issue-intentos-previos", "value"),
    State("edit-issue-intentos-durante", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_session_evolution(n_clicks, session_id, notes, modality, status, simple_issues,
                          alim, alim_desc, intra, intra_desc, gen, gen_desc, par, par_desc, crim, crim_desc, sex, sex_desc,
                          disid, disid_desc, disc, disc_desc, consumo, consumo_list, consumo_otro, enfer, enfer_desc,
                          suicidio_ini, suicidio_fin, intentos_prev, intentos_dur, token):
    if not n_clicks or not session_id or not token:
        return dash.no_update, dash.no_update, dash.no_update
        
    # Reconstruct worked issues dictionary
    worked_dict = {}
    
    # Simpler ones
    if simple_issues:
        for issue in simple_issues:
            worked_dict[issue] = True
            
    # Complex ones
    worked_dict["TRASTORNOS EN LA ALIMENTACIÓN"] = {"checked": bool(alim), "specify": alim_desc or ""}
    worked_dict["VIOLENCIA INTRAFAMILIAR"] = {"checked": bool(intra), "description": intra_desc or ""}
    worked_dict["VIOLENCIA DE GÉNERO"] = {"checked": bool(gen), "description": gen_desc or ""}
    worked_dict["VIOLENCIA DE PAREJA"] = {"checked": bool(par), "description": par_desc or ""}
    worked_dict["VIOLENCIA POR TEMAS CRIMINALES"] = {"checked": bool(crim), "description": crim_desc or ""}
    worked_dict["VIOLENCIA SEXUAL"] = {"checked": bool(sex), "description": sex_desc or ""}
    worked_dict["PERTENECE A LAS DISIDENCIAS"] = {"checked": bool(disid), "specify": disid_desc or ""}
    worked_dict["DISCAPACIDAD"] = {"checked": bool(disc), "specify": disc_desc or ""}
    worked_dict["ENFERMEDADES FÍSICAS"] = {"checked": bool(enfer), "specify": enfer_desc or ""}
    
    # Consumo
    worked_dict["CONSUMO PROBLEMÁTICO DE SUSTANCIAS"] = {
        "checked": bool(consumo),
        "substances": consumo_list or [],
        "otro": consumo_otro or ""
    }
    
    # Suicidio
    worked_dict["IDEACIÓN SUICIDA al iniciar el tratamiento"] = suicidio_ini
    worked_dict["IDEACIÓN SUICIDA al finalizar el tratamiento"] = suicidio_fin
    worked_dict["INTENTOS SUICIDAS PREVIOS ¿cuántos?"] = int(intentos_prev or 0)
    worked_dict["INTENTOS SUICIDAS DURANTE EL TRATAMIENTO ¿cuántos?"] = int(intentos_dur or 0)
    
    payload = {
        "session_date": datetime.now().isoformat(), # Just a placeholder since date is required in SessionBase schema but put checks date in session_db
        "modality": modality,
        "status": status,
        "therapist_notes": notes,
        "worked_issues": worked_dict
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.put(f"{API_URL}/sessions/{session_id}", json=payload, headers=headers)
        if res.status_code == 200:
            return "", False, False # Close modal, success
        else:
            return f"Error al guardar: {res.text}", True, True
    except Exception as e:
        return f"Error de conexión: {str(e)}", True, True

# --- Process Data Form Callbacks ---

# Visibility toggles for process data form
@callback(
    Output("div-proc-interrupcion", "style"),
    Output("div-proc-abandono", "style"),
    Output("div-proc-psiquiatria", "style"),
    Input("proc-estatus-proceso", "value"),
    Input("proc-canalizacion-psiquiatria", "value")
)
def toggle_process_subfields(estatus, psiquiatria):
    d_block = {"display": "block"}
    d_none = {"display": "none"}
    
    interrupcion_visible = d_block if estatus in ["Interrupción interna", "Interrupción externa"] else d_none
    abandono_visible = d_block if estatus in ["Abandono", "Suspensión"] else d_none
    psiquiatria_visible = d_block if psiquiatria == "true" else d_none
    
    return interrupcion_visible, abandono_visible, psiquiatria_visible

# Load process data
@callback(
    Output("proc-fecha-solicitud", "value"),
    Output("proc-fecha-inicio", "value"),
    Output("proc-semestre-inicio", "value"),
    Output("proc-edad", "value"),
    Output("proc-sexo", "value"),
    Output("proc-ano-cursa", "value"),
    Output("proc-sesiones-totales", "value"),
    Output("proc-inasistencias", "value"),
    Output("proc-horas-padres", "value"),
    Output("proc-horas-clinicas-actual", "value"),
    Output("proc-horas-clinicas-anterior", "value"),
    Output("proc-sesiones-seguimiento", "value"),
    Output("proc-estatus-proceso", "value"),
    Output("proc-motivo-interrupcion", "value"),
    Output("proc-observaciones-abandono", "value"),
    Output("proc-fecha-finalizacion", "value"),
    Output("proc-semestre-finalizacion", "value"),
    Output("proc-tuvo-intervencion-api", "value"),
    Output("proc-sesiones-api", "value"),
    Output("proc-impresion-diagnostica", "value"),
    Output("proc-internamientos-previos", "value"),
    Output("proc-internamientos-previos-cant", "value"),
    Output("proc-internamientos-durante", "value"),
    Output("proc-internamientos-durante-cant", "value"),
    Output("proc-canalizacion-psiquiatria", "value"),
    Output("proc-dx-psiquiatria", "value"),
    Output("proc-fecha-canalizacion", "value"),
    Output("proc-canalizacion-otra", "value"),
    Output("proc-canalizacion-otra-cual", "value"),
    Output("proc-referido-externo", "value"),
    Output("proc-intervencion-espora-comunitaria", "value"),
    Output("proc-intervencion-espora-comunitaria-cual", "value"),
    Input("current-case-id", "data"),
    Input("edit-session-modal", "is_open"), # Reload if session updated (recalculates hours/sessions)
    State("auth-token", "data")
)
def load_process_data(case_id, modal_open, token):
    if not token or not case_id or modal_open:
        return dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{API_URL}/cases/{case_id}/process-data", headers=headers)
    if res.status_code != 200:
        return [None] * 32
        
    data = res.json()
    
    def parse_date(date_str):
        if date_str:
            return date_str[:10]
        return None
        
    def parse_bool(bool_val):
        if bool_val is True:
            return "true"
        elif bool_val is False:
            return "false"
        return None
        
    return (
        parse_date(data.get("fecha_solicitud")),
        parse_date(data.get("fecha_inicio")),
        data.get("semestre_inicio"),
        data.get("edad"),
        data.get("sexo"),
        data.get("ano_cursa"),
        data.get("sesiones_totales"),
        data.get("inasistencias"),
        data.get("horas_padres"),
        data.get("horas_clinicas_actual"),
        data.get("horas_clinicas_anterior"),
        data.get("sesiones_seguimiento"),
        data.get("estatus_proceso"),
        data.get("motivo_interrupcion"),
        data.get("observaciones_abandono"),
        parse_date(data.get("fecha_finalizacion")),
        data.get("semestre_finalizacion"),
        parse_bool(data.get("tuvo_intervencion_api")),
        data.get("sesiones_api"),
        data.get("impresion_diagnostica"),
        parse_bool(data.get("internamientos_previos")),
        data.get("internamientos_previos_cant"),
        parse_bool(data.get("internamientos_durante")),
        data.get("internamientos_durante_cant"),
        parse_bool(data.get("canalizacion_psiquiatria")),
        data.get("dx_psiquiatria"),
        parse_date(data.get("fecha_canalizacion")),
        parse_bool(data.get("canalizacion_otra")),
        data.get("canalizacion_otra_cual"),
        parse_bool(data.get("referido_externo")),
        parse_bool(data.get("intervencion_espora_comunitaria")),
        data.get("intervencion_espora_comunitaria_cual")
    )

# Save process data
@callback(
    Output("process-data-alert", "children"),
    Output("process-data-alert", "is_open"),
    Output("process-data-alert", "color"),
    Input("btn-save-process-data", "n_clicks"),
    State("current-case-id", "data"),
    State("proc-fecha-solicitud", "value"),
    State("proc-fecha-inicio", "value"),
    State("proc-semestre-inicio", "value"),
    State("proc-edad", "value"),
    State("proc-sexo", "value"),
    State("proc-ano-cursa", "value"),
    State("proc-sesiones-totales", "value"),
    State("proc-inasistencias", "value"),
    State("proc-horas-padres", "value"),
    State("proc-horas-clinicas-actual", "value"),
    State("proc-horas-clinicas-anterior", "value"),
    State("proc-sesiones-seguimiento", "value"),
    State("proc-estatus-proceso", "value"),
    State("proc-motivo-interrupcion", "value"),
    State("proc-observaciones-abandono", "value"),
    State("proc-fecha-finalizacion", "value"),
    State("proc-semestre-finalizacion", "value"),
    State("proc-tuvo-intervencion-api", "value"),
    State("proc-sesiones-api", "value"),
    State("proc-impresion-diagnostica", "value"),
    State("proc-internamientos-previos", "value"),
    State("proc-internamientos-previos-cant", "value"),
    State("proc-internamientos-durante", "value"),
    State("proc-internamientos-durante-cant", "value"),
    State("proc-canalizacion-psiquiatria", "value"),
    State("proc-dx-psiquiatria", "value"),
    State("proc-fecha-canalizacion", "value"),
    State("proc-canalizacion-otra", "value"),
    State("proc-canalizacion-otra-cual", "value"),
    State("proc-referido-externo", "value"),
    State("proc-intervencion-espora-comunitaria", "value"),
    State("proc-intervencion-espora-comunitaria-cual", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_process_data(n_clicks, case_id, f_sol, f_ini, sem_ini, edad, sexo, ano, tot, inasist, hrs_p, hrs_act, hrs_ant, seg,
                      estatus, motivo, obs, f_fin, sem_fin, api_chk, api_cant, imp_diag, int_prev, int_prev_cant,
                      int_dur, int_dur_cant, psiq, psiq_dx, f_psiq, otra, otra_cual, ref_ext, esp_com, esp_com_cual, token):
    if not n_clicks or not case_id or not token:
        return dash.no_update, dash.no_update, dash.no_update
        
    def to_datetime(date_str):
        if date_str:
            return f"{date_str}T00:00:00Z"
        return None
        
    def to_bool(val_str):
        if val_str == "true":
            return True
        elif val_str == "false":
            return False
        return None
        
    payload = {
        "fecha_solicitud": to_datetime(f_sol),
        "fecha_inicio": to_datetime(f_ini),
        "semestre_inicio": sem_ini or None,
        "edad": int(edad) if edad is not None else None,
        "sexo": sexo or None,
        "ano_cursa": int(ano) if ano is not None else None,
        "sesiones_totales": int(tot) if tot is not None else None,
        "inasistencias": int(inasist) if inasist is not None else None,
        "horas_padres": int(hrs_p) if hrs_p is not None else None,
        "horas_clinicas_actual": int(hrs_act) if hrs_act is not None else None,
        "horas_clinicas_anterior": int(hrs_ant) if hrs_ant is not None else None,
        "sesiones_seguimiento": int(seg) if seg is not None else None,
        "estatus_proceso": estatus or None,
        "motivo_interrupcion": motivo or None,
        "observaciones_abandono": obs or None,
        "fecha_finalizacion": to_datetime(f_fin),
        "semestre_finalizacion": sem_fin or None,
        "tuvo_intervencion_api": to_bool(api_chk),
        "sesiones_api": int(api_cant) if api_cant is not None else None,
        "impresion_diagnostica": imp_diag or None,
        "internamientos_previos": to_bool(int_prev),
        "internamientos_previos_cant": int(int_prev_cant) if int_prev_cant is not None else None,
        "internamientos_durante": to_bool(int_dur),
        "internamientos_durante_cant": int(int_dur_cant) if int_dur_cant is not None else None,
        "canalizacion_psiquiatria": to_bool(psiq),
        "dx_psiquiatria": psiq_dx or None,
        "fecha_canalizacion": to_datetime(f_psiq),
        "canalizacion_otra": to_bool(otra),
        "canalizacion_otra_cual": otra_cual or None,
        "referido_externo": to_bool(ref_ext),
        "intervencion_espora_comunitaria": to_bool(esp_com),
        "intervencion_espora_comunitaria_cual": esp_com_cual or None
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.put(f"{API_URL}/cases/{case_id}/process-data", json=payload, headers=headers)
        if res.status_code == 200:
            return "¡Datos de control de proceso guardados con éxito!", True, "success"
        else:
            return f"Error al guardar: {res.text}", True, "danger"
    except Exception as e:
        return f"Error de conexión: {str(e)}", True, "danger"

@callback(
    Output("quick-submission-upload-store", "data", allow_duplicate=True),
    Output("quick-submission-upload-preview", "children", allow_duplicate=True),
    Input("quick-submission-upload", "contents"),
    State("quick-submission-upload", "filename"),
    prevent_initial_call=True
)
def handle_quick_file_upload(contents, filename):
    if not contents:
        return None, ""
    try:
        header, base64_data = contents.split(",", 1)
        content_type = header.split(";")[0].replace("data:", "")
        preview = f"✓ Archivo cargado: {filename} ({content_type})"
        store_data = {
            "filename": filename,
            "content_type": content_type,
            "file_data": base64_data
        }
        return store_data, preview
    except Exception as e:
        return None, f"Error al procesar el archivo: {str(e)}"

@callback(
    Output("quick-submission-alert", "children"),
    Output("quick-submission-alert", "is_open"),
    Output("quick-submission-alert", "color"),
    Output("quick-submission-free-notes", "value"),
    Output("quick-submission-upload-store", "data", allow_duplicate=True),
    Output("quick-submission-upload-preview", "children", allow_duplicate=True),
    Input("btn-submit-quick-submission", "n_clicks"),
    State("quick-submission-free-notes", "value"),
    State("quick-submission-upload-store", "data"),
    State("current-case-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_quick_submission(n_clicks, free_notes_val, upload_data, case_id, token):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    if (not free_notes_val or not free_notes_val.strip()) and not upload_data:
        return "Debe escribir una nota o adjuntar un archivo.", True, "warning", dash.no_update, dash.no_update, dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    
    template_id = None
    try:
        res = requests.get(f"{API_URL}/fields/templates", headers=headers)
        if res.status_code == 200:
            templates = res.json()
            for t in templates:
                if t["name"] == "Nota Libre / Expediente Físico (Adjunto)":
                    template_id = t["id"]
                    break
    except Exception as e:
        return f"Error al consultar plantillas: {str(e)}", True, "danger", dash.no_update, dash.no_update, dash.no_update
        
    if not template_id:
        return "No se encontró la plantilla 'Nota Libre / Expediente Físico (Adjunto)' en el sistema.", True, "danger", dash.no_update, dash.no_update, dash.no_update
        
    attachments_payload = []
    
    # Handle manual free notes as a text file attachment
    if free_notes_val and free_notes_val.strip():
        import base64
        encoded_note = base64.b64encode(free_notes_val.encode("utf-8")).decode("utf-8")
        attachments_payload.append({
            "filename": "nota_libre.txt",
            "content_type": "text/plain",
            "file_data": encoded_note
        })
        
    # Handle uploaded file attachment
    if upload_data:
        attachments_payload.append(upload_data)
        
    payload = {
        "form_template_id": template_id,
        "case_id": int(case_id),
        "fields": [],
        "attachments": attachments_payload
    }
    
    try:
        res = requests.post(f"{API_URL}/fields/submissions", json=payload, headers=headers)
        if res.status_code == 200:
            return "Anexo guardado exitosamente en el expediente.", True, "success", "", None, ""
        else:
            return f"Error al guardar el anexo: {res.text}", True, "danger", dash.no_update, dash.no_update, dash.no_update
    except Exception as e:
        return f"Error de conexión: {str(e)}", True, "danger", dash.no_update, dash.no_update, dash.no_update

@callback(
    Output("download-history-file", "data"),
    Input("btn-download-history", "n_clicks"),
    State("current-case-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def download_patient_history(n_clicks, case_id, token):
    if not n_clicks or not case_id:
        return dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/export/case/{case_id}", headers=headers)
        if res.status_code == 200:
            filename = f"historial_caso_{case_id}.xlsx"
            cd = res.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                filename = cd.split("filename=")[1].strip('"')
            return dcc.send_bytes(res.content, filename=filename)
    except Exception as e:
        print("Error downloading patient history:", e)
    return dash.no_update


# --- Callbacks para Envío de Correos al Consultante ---

@callback(
    Output("email-patient-modal", "is_open"),
    Input("btn-open-email-modal", "n_clicks"),
    Input("btn-cancel-email-modal", "n_clicks"),
    State("email-patient-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_email_modal(open_clicks, cancel_clicks, is_open):
    return not is_open

@callback(
    Output("div-email-form-select", "style"),
    Output("email-form-select", "options"),
    Input("email-template-type", "value"),
    Input("email-patient-modal", "is_open"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def handle_email_template_type(template_type, is_open, token):
    form_select_style = {"display": "block"} if template_type == "form" else {"display": "none"}
    
    options = [
        {"label": "📋 Información Complementaria de Inicio (LimeSurvey #228334)", "value": "LS_228334"},
        {"label": "🏁 Formato de Egreso y Satisfacción CRES-4 (LimeSurvey #338334)", "value": "LS_338334"},
    ]
    if token and is_open:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            res = requests.get(f"{API_URL}/fields/templates", headers=headers)
            if res.status_code == 200:
                templates = res.json()
                for t in templates:
                    options.append({"label": t["name"], "value": t["name"]})
        except Exception as e:
            print("Error loading form templates for email:", e)
            
    return form_select_style, options

@callback(
    Output("email-recipient-input", "value"),
    Output("email-subject-input", "value"),
    Output("email-body-textarea", "value"),
    Input("email-patient-modal", "is_open"),
    Input("email-template-type", "value"),
    Input("email-form-select", "value"),
    State("current-case-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def update_email_content(is_open, template_type, form_name, case_id, token):
    if not is_open or not case_id or not token:
        return dash.no_update, dash.no_update, dash.no_update

    headers = {"Authorization": f"Bearer {token}"}
    participant_email = ""
    participant_name = "Consultante"
    participant_folio = ""
    participant_account = ""
    therapist_name = "Tu terapeuta asignado"
    next_session_str = "No agendada aún"
    next_session_modality = "Por definir"

    try:
        # Fetch current user info for therapist name
        user_res = requests.get(f"{API_URL}/users/me", headers=headers)
        if user_res.status_code == 200:
            user_data = user_res.json()
            therapist_name = user_data.get("full_name") or user_data.get("email", "").split("@")[0].capitalize()
            
        # Fetch case data
        cases_res = requests.get(f"{API_URL}/cases", headers=headers)
        if cases_res.status_code == 200:
            cases = cases_res.json()
            case_data = next((c for c in cases if str(c["id"]) == str(case_id)), None)
            if case_data:
                p = case_data.get("participant", {})
                participant_name = p.get("full_name", "Consultante")
                participant_email = p.get("email", "")
                participant_folio = p.get("anonymous_folio", "")
                participant_account = p.get("student_account", "")

                sessions = case_data.get("sessions", [])
                now = datetime.now()
                future_sessions = []
                for s in sessions:
                    try:
                        s_date = datetime.fromisoformat(s["session_date"].replace("Z", "+00:00")).replace(tzinfo=None)
                        if s_date >= now or s.get("status") == "scheduled":
                            future_sessions.append((s_date, s))
                    except Exception:
                        pass
                        
                if future_sessions:
                    future_sessions.sort(key=lambda x: x[0])
                    next_s_date, next_s = future_sessions[0]
                    next_session_str = next_s_date.strftime("%d/%m/%Y a las %H:%M hrs")
                    modality_val = next_s.get("modality")
                    if modality_val == "online":
                        next_session_modality = "En Línea"
                    elif modality_val == "in_person":
                        next_session_modality = "Presencial"
                    elif modality_val:
                        next_session_modality = str(modality_val).capitalize()
    except Exception as e:
        print("Error fetching details for email pre-fill:", e)

    if template_type == "appointment":
        subject = "Recordatorio de Próxima Cita - Programa ESPORA"
        body = (
            f"Hola {participant_name},\n\n"
            f"Esperamos que te encuentres muy bien.\n"
            f"Te recordamos que tienes una cita agendada para el {next_session_str} en modalidad {next_session_modality}.\n\n"
            f"Por favor confírmanos tu asistencia o infórmanos con anticipación en caso de requerir algún cambio de horario.\n\n"
            f"Saludos cordiales,\n"
            f"{therapist_name}\n"
            f"Programa ESPORA"
        )
    elif template_type == "form":
        folio_ref = participant_folio or participant_account
        if form_name == "LS_228334":
            ls_url = f"https://ls-test.c3.unam.mx/228334?newtest=Y&lang=es-MX&folio={folio_ref}"
            subject = "Cuestionario de Información de Inicio - Programa ESPORA"
            body = (
                f"Hola {participant_name},\n\n"
                f"Para completar tu expediente clínico de inicio en el Programa ESPORA, te pedimos responder este breve cuestionario (toma menos de 5 minutos):\n\n"
                f"🔗 Enlace directo: {ls_url}\n"
                f"📌 Tu Folio ESPORA: {participant_folio or 'N/D'} (o No. de cuenta: {participant_account or 'N/D'})\n\n"
                f"Muchas gracias,\n"
                f"{therapist_name}\n"
                f"Programa ESPORA"
            )
        elif form_name == "LS_338334":
            ls_url = f"https://ls-test.c3.unam.mx/338334?newtest=Y&lang=es-MX&folio={folio_ref}"
            subject = "Cuestionario de Egreso y Satisfacción (CRES-4) - Programa ESPORA"
            body = (
                f"Hola {participant_name},\n\n"
                f"Queremos conocer tu opinión sobre el Programa ESPORA y sobre la atención que recibiste durante estas semanas con el objetivo de seguir mejorando.\n\n"
                f"Por favor responde el siguiente cuestionario confidencial de cierre:\n"
                f"🔗 Enlace directo: {ls_url}\n"
                f"📌 Tu Folio ESPORA: {participant_folio or 'N/D'} (o No. de cuenta: {participant_account or 'N/D'})\n\n"
                f"¡Muchas gracias por tu confianza!\n"
                f"{therapist_name}\n"
                f"Programa ESPORA"
            )
        else:
            selected_form = form_name or "Cuestionario de Seguimiento"
            subject = f"Formulario por responder: {selected_form} - Programa ESPORA"
            body = (
                f"Hola {participant_name},\n\n"
                f"Por favor contesta este cuestionario ({selected_form}) antes de nuestra próxima cita.\n\n"
                f"Puedes ingresar a la plataforma institucional ESPORA con tu correo para completar tus respuestas.\n\n"
                f"Saludos cordiales,\n"
                f"{therapist_name}\n"
                f"Programa ESPORA"
            )
    else:  # blank
        subject = ""
        body = ""

    return participant_email, subject, body

@callback(
    Output("email-send-alert", "children"),
    Output("email-send-alert", "is_open"),
    Output("email-send-alert", "color"),
    Input("btn-send-email-submit", "n_clicks"),
    State("current-case-id", "data"),
    State("email-recipient-input", "value"),
    State("email-subject-input", "value"),
    State("email-body-textarea", "value"),
    State("email-template-type", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def execute_send_email(n_clicks, case_id, recipient, subject, body, email_type, token):
    if not n_clicks or not case_id or not token:
        return dash.no_update, False, "danger"

    if not recipient or not recipient.strip():
        return "Por favor especifica un correo destinatario válido.", True, "danger"

    if not subject or not subject.strip():
        return "Por favor ingresa un asunto para el correo.", True, "danger"

    if not body or not body.strip():
        return "El cuerpo del correo no puede estar vacío.", True, "danger"

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "recipient_email": recipient.strip(),
        "subject": subject.strip(),
        "body": body.strip(),
        "email_type": email_type or "custom"
    }

    try:
        res = requests.post(f"{API_URL}/cases/{case_id}/send-email", json=payload, headers=headers)
        if res.status_code == 200:
            res_data = res.json()
            msg = res_data.get("message", f"Correo enviado exitosamente a {recipient}")
            return msg, True, "success"
        else:
            err_msg = res.json().get("detail", res.text)
            return f"Error al enviar correo: {err_msg}", True, "danger"
    except Exception as e:
        return f"Error de conexión al servidor: {str(e)}", True, "danger"

