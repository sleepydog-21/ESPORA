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
            dbc.Col(html.H2(id="patient-title", className="my-4"), width=8),
            dbc.Col(
                dbc.Button("Volver al Panel", href="/therapist", color="secondary", className="mt-4 float-end"),
                width=4
            )
        ]),
        
        dbc.Row([
            # Columna Izquierda: Información y Control
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Resumen del Paciente")),
                    dbc.CardBody([
                        html.Div(id="patient-info-content"),
                        html.Hr(),
                        html.H6("Expediente (Rubros Dinámicos)"),
                        dcc.Loading(
                            type="circle",
                            children=html.Div(id="dynamic-fields-form", className="mt-3")
                        ),
                        dbc.Button("Guardar Cambios", id="btn-save-dynamic-fields", color="primary", size="sm", className="mt-3 w-100"),
                        dbc.Alert("", id="alert-save-dynamic-fields", is_open=False, color="success", className="mt-2", duration=3000)
                    ])
                ], className="mb-4 shadow-sm border-primary"),
                
                dbc.Card([
                    dbc.CardHeader(html.H5("Módulo de Encuestas")),
                    dbc.CardBody([
                        html.P("Herramientas para evaluación y seguimiento:", className="text-muted"),
                        dbc.Button("Mandar Encuesta", id="btn-send-survey", color="warning", className="w-100 mb-2"),
                        dbc.Button("Rellenar Evaluación Propia", id="btn-fill-survey", color="info", className="w-100 mb-2")
                    ])
                ], className="mb-4 shadow-sm border-warning")
            ], width=12, md=4),
            
            # Columna Derecha: Sesiones
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(dbc.Row([
                        dbc.Col(html.H5("Línea de Tiempo del Tratamiento")),
                        dbc.Col(dbc.Button("Agendar Única", id="btn-open-schedule", color="primary", size="sm", className="float-end"), width="auto")
                    ])),
                    dbc.CardBody([
                        html.Div(id='sessions-timeline-container', style={'maxHeight': '600px', 'overflowY': 'auto'})
                    ])
                ], className="shadow-sm border-info")
            ], width=12, md=8)
        ]),
        
        # Modal para Agendar
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
        
        # Modal para Mandar Encuestas
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Catálogo de Encuestas")),
            dbc.ModalBody([
                html.P("Selecciona la evaluación que necesitas mandar. Se enviará un correo con el enlace personalizado.", className="text-muted mb-3"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("BDI-II (Inventario de Depresión de Beck)", className="mb-1 fw-bold"),
                            html.Small("Evaluación Inicial", className="text-muted")
                        ], className="d-flex w-100 justify-content-between"),
                        dbc.Badge("Contestada ✅", color="success", className="mt-2 fs-6"),
                        html.Span(" (Último envío: 10-Mar-2026 | Contestada: 12-Mar-2026)", className="text-muted small ms-2")
                    ], className="mb-2 border rounded"),
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("BAI (Inventario de Ansiedad de Beck)", className="mb-1 fw-bold"),
                            html.Small("Evaluación Inicial", className="text-muted")
                        ], className="d-flex w-100 justify-content-between"),
                        dbc.Badge("Enviada (Sin contestar) ⏳", color="warning", className="mt-2 text-dark fs-6"),
                        html.Span(" (Último envío: 15-Mar-2026)", className="text-muted small ms-2"),
                        dbc.Button("Reenviar Link", color="outline-primary", size="sm", className="float-end ms-2 mt-1")
                    ], className="mb-2 border rounded"),
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("SCL-90 (Cuestionario de Síntomas)", className="mb-1 fw-bold"),
                            html.Small("Batería General", className="text-muted")
                        ], className="d-flex w-100 justify-content-between"),
                        dbc.Badge("Pendiente de enviar ✉️", color="secondary", className="mt-2 text-dark fs-6"),
                        dbc.Button("Enviar Link", color="primary", size="sm", className="float-end ms-2 mt-1")
                    ], className="mb-2 border rounded")
                ], flush=True)
            ]),
            dbc.ModalFooter([
                dbc.Button("Cerrar", id="btn-close-survey-modal", color="secondary", className="ms-auto")
            ])
        ], id="send-survey-modal", is_open=False, size="lg")
    ])

# Callbacks
@callback(
    Output("patient-title", "children"),
    Output("patient-info-content", "children"),
    Output("sessions-timeline-container", "children"),
    Input("current-case-id", "data"),
    Input("schedule-patient-modal", "is_open"), # Refresh table when modal closes
    State("auth-token", "data")
)
def load_patient_data(case_id, modal_open, token):
    if not token or not case_id or modal_open:
        return dash.no_update, dash.no_update, dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/cases", headers=headers)
        if res.status_code == 200:
            cases = res.json()
            case_data = next((c for c in cases if str(c['id']) == str(case_id)), None)
            
            if case_data:
                p = case_data['participant']
                title = f"Expediente Clínico y Sesiones: {p['full_name']}"
                
                status_map = {"waiting": "Lista de Espera", "assigned": "Asignado", "active": "Activo", "closed": "Cerrado"}
                
                info = [
                    html.P([html.Strong("No. Cuenta: "), p.get('student_account')]),
                    html.P([html.Strong("Email: "), p.get('email')]),
                    html.P([html.Strong("Facultad: "), p.get('faculty', 'N/D')]),
                    html.P([html.Strong("Teléfono: "), p.get('phone', 'N/D')]),
                    html.P([html.Strong("Estado del Caso: "), status_map.get(case_data['status'], case_data['status'])]),
                    html.Hr(),
                    dbc.Button("🚨 Activar Bandera Roja de Peligro", id="btn-panic-alert", color="danger", size="sm", outline=True, className="w-100")
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
                    
                    bg_color = "primary" if status == "scheduled" else "success" if status == "completed" else "danger"
                    
                    card = dbc.Card([
                        dbc.CardHeader([
                            html.Strong(f"Estado de la Cita: {status.upper()}"),
                            html.Span(f" - {parsed_date}", className="text-muted float-end pb-1")
                        ]),
                        dbc.CardBody(html.P(notes, className="mb-0 small"))
                    ], color=bg_color, outline=True, className="mb-3")
                    timeline_ui.append(card)
                    
                if not timeline_ui:
                    timeline_ui = [html.P("El paciente aún no cuenta con historial de sesiones clínicas programadas en su expediente.", className="text-muted small")]
                
                return title, info, timeline_ui
    except Exception as e:
        print(f"Error loading patient data: {e}")
        
    return "Error cargando paciente", html.P("No se pudo cargar la información.", className="text-danger"), []

@callback(
    Output("schedule-patient-modal", "is_open"),
    [Input("btn-open-schedule", "n_clicks"), Input("btn-cancel-schedule", "n_clicks"), Input("btn-submit-schedule", "n_clicks")],
    [State("schedule-patient-modal", "is_open"), State("new-session-date", "value"), State("new-session-modality", "value"), State("current-case-id", "data"), State("auth-token", "data")],
    prevent_initial_call=True
)
def handle_schedule_modal(n_open, n_cancel, n_submit, is_open, date_val, modality, case_id, token):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-open-schedule":
        return True
    elif trigger_id == "btn-cancel-schedule":
        return False
    elif trigger_id == "btn-submit-schedule" and date_val and modality:
        headers = {"Authorization": f"Bearer {token}"}
        dt = datetime.fromisoformat(date_val).isoformat() + "Z"
        try:
            requests.post(
                f"{API_URL}/cases/{case_id}/sessions",
                json={"case_id": int(case_id), "session_date": dt, "modality": modality},
                headers=headers
            )
            return False
        except Exception as e:
            print(f"Error scheduling: {e}")
            
    return is_open

@callback(
    Output("send-survey-modal", "is_open"),
    [Input("btn-send-survey", "n_clicks"), Input("btn-close-survey-modal", "n_clicks")],
    [State("send-survey-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_survey_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("dynamic-fields-form", "children"),
    Input("current-case-id", "data"),
    State("auth-token", "data"),
)
def load_dynamic_fields(case_id, token):
    if not token or not case_id:
        return dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res_def = requests.get(f"{API_URL}/fields", headers=headers)
        res_val = requests.get(f"{API_URL}/fields/case/{case_id}/values", headers=headers)
        
        if res_def.status_code == 200 and res_val.status_code == 200:
            definitions = res_def.json()
            values = res_val.json()
            
            form_elements = []
            for field in definitions:
                val = values.get(field["name"], "")
                
                if field["field_type"] == "text":
                    input_component = dbc.Textarea(
                        id={"type": "dynamic-input", "index": field["name"]},
                        value=val,
                        className="mb-2"
                    )
                else:
                    input_component = dbc.Input(
                        id={"type": "dynamic-input", "index": field["name"]},
                        value=val,
                        type="text" if field["field_type"] == "string" else "number",
                        className="mb-2"
                    )
                
                form_elements.append(html.Div([
                    dbc.Label(field["label"], className="small fw-bold text-muted mb-0"),
                    input_component
                ]))
                
            if not form_elements:
                return html.P("No hay rubros de expediente configurados.", className="text-muted small")
                
            return form_elements
            
    except Exception as e:
        print("Error loading dynamic fields:", e)
        
    return html.P("Error cargando expediente.", className="text-danger small")

@callback(
    Output("alert-save-dynamic-fields", "children"),
    Output("alert-save-dynamic-fields", "color"),
    Output("alert-save-dynamic-fields", "is_open"),
    Input("btn-save-dynamic-fields", "n_clicks"),
    State({"type": "dynamic-input", "index": dash.ALL}, "value"),
    State({"type": "dynamic-input", "index": dash.ALL}, "id"),
    State("current-case-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_dynamic_fields(n_clicks, values, ids, case_id, token):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    
    fields_payload = {}
    for idx, val in zip(ids, values):
        fields_payload[idx["index"]] = val
        
    try:
        res = requests.put(
            f"{API_URL}/fields/case/{case_id}/values",
            json={"fields": fields_payload},
            headers=headers
        )
        if res.status_code == 200:
            return "¡Expediente guardado con éxito!", "success", True
        else:
            return f"Error: {res.text}", "danger", True
    except Exception as e:
        return f"Error de conexión: {e}", "danger", True
