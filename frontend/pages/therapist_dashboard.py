import dash
from dash import html, dcc, callback, Input, Output, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import requests
import os
import json
from datetime import datetime, timedelta

dash.register_page(__name__, path='/therapist', name='Therapist Dashboard')

API_URL = os.getenv("API_URL", "http://localhost:8000")

layout = dbc.Container([
    dcc.Location(id="therapist-url"),
    dcc.Interval(id="therapist-interval", interval=60000, n_intervals=0), # Auto refresh 1 min
    
    dbc.Row([
        dbc.Col([
            html.H2("Mi Consultorio 🩺", className="my-2 text-primary"),
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Resumen Semanal", className="card-subtitle text-muted mb-2"),
                    html.Div([
                        dbc.Badge("Totales: 0", id="badge-total", color="primary", className="me-2 fs-6"),
                        dbc.Badge("Programadas: 0", id="badge-scheduled", color="secondary", className="me-2 fs-6"),
                        dbc.Badge("Completadas: 0", id="badge-completed", color="success", className="fs-6")
                    ])
                ], className="py-2")
            ], className="mb-3")
        ], width=8)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Button("📅 Agendar Cita Única", id="btn-add-single", color="outline-primary", className="mb-4 float-end mx-2"),
            dbc.Button("🗓️ Iniciar Protocolo Bi-semanal", id="btn-open-protocol", color="primary", className="mb-4 float-end")
        ], width=12)
    ]),

    dbc.Row([
        # Calendario Semanal
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Mi Calendario de Sesiones (Próximos 14 días)")),
                dbc.CardBody([
                    dcc.Store(id='cal-events-store', data=[]),
                    dcc.Store(id='trigger-reload-calendar', data=0),
                    html.Div(id='calendar-dummy-output', style={'display': 'none'}),
                    dcc.Input(id='cal-date-clicked', type='hidden'),
                    dcc.Input(id='cal-event-clicked', type='hidden'),
                    dcc.Input(id='cal-event-dropped', type='hidden'),
                    dbc.Button("+ Nueva Cita Manual", id="btn-new-apt", color="success", size="sm", className="mb-2"),
                    html.Div(id='calendar-div', style={"height": "600px"}),
                    html.P("Haz clic en cualquier punto del calendario para modificar la cita o agregarle notas de evolución.", className="text-muted small mt-2")
                ])
            ], className="mb-4 shadow-sm")
        ], width=12, lg=8),
        
        # Pacientes (My Cases)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Mis Pacientes (Selecciona para agendar)")),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='cases-table',
                        columns=[],
                        data=[],
                        style_table={'overflowX': 'auto', 'height': '500px'},
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                        markdown_options={"html": True}
                    )
                ])
            ], className="mb-4 shadow-sm")
        ], width=12, lg=4)
    ]),

    # Modal Cita Única
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Agendar Cita Única (Manual)")),
        dbc.ModalBody([
            html.P("Selecciona la fecha y hora exacta para crear una nueva cita en el calendario.", className="text-muted small"),
            dbc.Label("Seleccionar Paciente Activo:"),
            dcc.Dropdown(id="single-case-dropdown", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Fecha de la Sesión:"),
                    dbc.Input(id="single-start-date", type="date", className="mb-3")
                ]),
                dbc.Col([
                    dbc.Label("Hora de la Sesión:"),
                    dbc.Input(id="single-start-time", type="time", className="mb-3")
                ])
            ]),
            dbc.Button("Agendar en Calendario", id="btn-submit-single", color="success", className="w-100")
        ])
    ], id="modal-single", is_open=False),

    # Modal Protocolo Bi-semanal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Lanzar Protocolo Bi-semanal (Generación Predictiva)")),
        dbc.ModalBody([
            html.P("El motor generará citas automáticamente cada 14 días a la misma hora para el paciente."),
            dbc.Label("Seleccionar Paciente Activo:"),
            dcc.Dropdown(id="protocol-case-dropdown", className="mb-3"),
            dbc.Label("Fecha de la Primera Sesión:"),
            dbc.Input(id="protocol-start-date", type="date", className="mb-3"),
            dbc.Label("Hora Inicial:"),
            dbc.Input(id="protocol-start-time", type="time", className="mb-3"),
            dbc.Button("Generar y Asignar Sesiones", id="btn-submit-protocol", color="success", className="w-100")
        ])
    ], id="modal-protocol", is_open=False),


    # Appointment Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Detalles de Cita", id="apt-modal-title")),
        dbc.ModalBody([
            dbc.Input(id="apt-id", type="hidden"),
            html.Label("Paciente / Caso"),
            dcc.Dropdown(id="apt-case-id", placeholder="Opcional: Selecciona un paciente..."),
            html.Br(),
            html.Label("Estado"),
            dcc.Dropdown(id="apt-status", options=[
                {"label": "Programada", "value": "scheduled"},
                {"label": "Llevada a cabo", "value": "completed"},
                {"label": "Cancelada", "value": "cancelled"}
            ], value="scheduled"),
            html.Br(),
            html.Label("Inicio"),
            dbc.Input(id="apt-start", type="datetime-local", step=1800),
            html.Br(),
            html.Label("Fin"),
            dbc.Input(id="apt-end", type="datetime-local", step=1800),
            html.Br(),
            html.Label("Notas o Detalles"),
            dbc.Textarea(id="apt-notes"),
            html.Br(),
            html.Label("Temas Identificados (Selecciona todos los que apliquen)"),
            dcc.Checklist(
                id="apt-topics-checklist",
                options=[],
                value=[],
                labelStyle={"display": "block", "marginLeft": "10px"},
                inputStyle={"marginRight": "5px"}
            ),
            html.Br(),
            html.Div(
                dbc.Switch(id="apt-biweekly-switch", label="Agendar Protocolo Bi-semanal completo (12 citas)", value=False, className="mt-2"),
                id="biweekly-switch-container"
            ),
            html.Div(id="apt-error", className="text-danger mt-2")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar Cita", id="btn-cancel-apt", color="danger", className="me-auto", style={"display": "none"}),
            dbc.Button("Guardar", id="btn-save-apt", color="success"),
            dbc.Button("Cerrar", id="btn-close-apt", color="secondary")
        ])
    ], id="apt-modal", is_open=False),

    # Register clientside callback for JS FullCalendar
    dcc.Store(id='close-modal-trigger', data=0),
    html.Div(id='calendar-dummy-output', style={'display': 'none'}),
    dcc.Input(id='cal-view-range', type='hidden'),
    dcc.Input(id='cal-status-quick-change', type='hidden'),

    # Modal de Feedback Semanal (Burnout)
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("🩺 Encuesta Semanal de Bienestar y Respaldo")),
        dbc.ModalBody([
            html.P("Como parte de nuestro compromiso con el cuidado de tu salud mental y el acompañamiento clínico en el programa ESPORA, te pedimos responder brevemente a estas 2 preguntas. Solo te tomará unos segundos:", className="text-muted small"),
            html.Hr(),
            
            # Pregunta 1
            html.Label("1. Del 1 al 10, ¿qué tanto sientes que las demandas administrativas o de volumen interfieren con tu capacidad de escucha analítica?", className="fw-bold small mb-2 d-block"),
            html.Div(
                dcc.Slider(
                    id="feedback-q1",
                    min=1, max=10, step=1,
                    marks={i: str(i) for i in range(1, 11)},
                    value=5,
                ),
                className="mb-4 px-2"
            ),
            
            # Pregunta 2
            html.Label("2. Del 1 al 10, ¿qué tan respaldado/a y acompañado/a te sientes por el programa para manejar los casos de alta complejidad o riesgo de este plantel?", className="fw-bold small mb-2 d-block"),
            html.Div(
                dcc.Slider(
                    id="feedback-q2",
                    min=1, max=10, step=1,
                    marks={i: str(i) for i in range(1, 11)},
                    value=5,
                ),
                className="mb-4 px-2"
            ),
            
            dbc.Alert(id="feedback-alert", is_open=False, color="danger", className="mt-2")
        ]),
        dbc.ModalFooter([
            dbc.Button("Omitir por ahora", id="btn-skip-feedback", color="secondary", className="me-auto"),
            dbc.Button("Enviar Respuestas", id="btn-submit-feedback", color="success")
        ])
    ], id="feedback-modal", is_open=False, backdrop="static", keyboard=False)
], fluid=True)

dash.clientside_callback(
    """
    function(events, dummy) {
        return window.dash_clientside.calendar.initCalendar(events, 'calendar-div');
    }
    """,
    Output('calendar-dummy-output', 'children'),
    Input('cal-events-store', 'data'),
    Input('calendar-dummy-output', 'id') # dummy input to trigger once
)

@callback(
    Output("cal-events-store", "data"),
    Input("therapist-url", "pathname"),
    Input("trigger-reload-calendar", "data"),
    Input("cal-event-dropped", "value"),
    State("auth-token", "data")
)
def load_calendar_events(path, reload_trigger, drop_value, token):
    print(f"DEBUG Python: load_calendar_events triggered with token={bool(token)}")
    if not token:
        return []
        
    headers = {"Authorization": f"Bearer {token}"}
    
    # Handle Drop Event Patch (if drop_value changed)
    ctx = dash.callback_context
    if ctx.triggered and "cal-event-dropped" in ctx.triggered[0]["prop_id"] and drop_value:
        try:
            # Value comes as JSON string + _ts
            json_str = drop_value.split("_|ts|_")[0]
            drop_data = json.loads(json_str)
            requests.patch(f"{API_URL}/appointments/{drop_data['id']}", json={
                "start_time": drop_data['start'],
                "end_time": drop_data['end']
            }, headers=headers)
        except Exception as e:
            print("Drop Error:", e)

    # Reload all events
    res = requests.get(f"{API_URL}/appointments", headers=headers)
    print(f"DEBUG: GET /appointments returned {res.status_code}")
    if res.status_code == 200:
        apts = res.json()
        print(f"DEBUG: Fetched {len(apts)} appointments from API")
        
        def get_color(case_id):
            if not case_id: return "#6c757d" # Gris oscuro para citas sin caso
            # Paleta de colores expandida y distintiva
            colors = [
                "#007bff", "#28a745", "#dc3545", "#fd7e14", "#6f42c1", 
                "#e83e8c", "#20c997", "#17a2b8", "#6610f2", "#d63384"
            ]
            import hashlib
            # Usar un hash del ID para asegurar distribución pseudo-aleatoria estable
            hash_idx = int(hashlib.md5(str(case_id).encode()).hexdigest(), 16)
            return colors[hash_idx % len(colors)]
            
        events = []
        for apt in apts:
            status_prefix = ""
            if apt.get('status') == 'completed':
                status_prefix = "✅ "
            elif apt.get('status') == 'cancelled':
                status_prefix = "❌ "
                
            base_title = f"Caso {apt['case_id']}" if apt.get('case_id') else (apt.get('notes') or 'Cita')
            
            events.append({
                "id": str(apt['id']),
                "title": f"{status_prefix}{base_title}",
                "start": apt['start_time'],
                "end": apt['end_time'],
                "context": apt['notes'],
                "case_id": apt['case_id'],
                "status": apt['status'],
                "color": get_color(apt.get('case_id'))
            })
        print(f"DEBUG: Returning events to Dash: {events}")
        return events
    return []

@callback(
    Output("apt-modal", "is_open"),
    Output("apt-id", "value"),
    Output("apt-start", "value"),
    Output("apt-end", "value"),
    Output("apt-notes", "value"),
    Output("apt-case-id", "value"),
    Output("apt-status", "value"),
    Output("apt-biweekly-switch", "value"),
    Output("biweekly-switch-container", "style"),
    Output("btn-cancel-apt", "style"),
    Output("apt-topics-checklist", "options"),
    Output("apt-topics-checklist", "value"),
    Input("cal-date-clicked", "value"),
    Input("cal-event-clicked", "value"),
    Input("btn-new-apt", "n_clicks"),
    Input("btn-close-apt", "n_clicks"),
    Input("btn-cancel-apt", "n_clicks"),
    Input("close-modal-trigger", "data"),
    State("apt-modal", "is_open"),
    State("cal-events-store", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def toggle_modal(date_clicked, event_clicked, new_click, close_click, cancel_click, close_modal_trigger, is_open, events, token):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Fetch topics for options
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    topics_options = []
    if token:
        try:
            res_topics = requests.get(f"{API_URL}/topics/", headers=headers)
            if res_topics.status_code == 200:
                topics_options = [{"label": t["name"], "value": t["id"]} for t in res_topics.json()]
        except:
            pass
            
    if trigger_id in ["btn-close-apt", "btn-cancel-apt", "close-modal-trigger"]:
        return False, "", "", "", "", None, "scheduled", False, {"display": "none"}, {"display": "none"}, [], []
        
    if trigger_id == "btn-new-apt":
        return True, "", "", "", "", None, "scheduled", False, {"display": "block"}, {"display": "none"}, topics_options, []
        
    if trigger_id == "cal-date-clicked" and date_clicked:
        # date_clicked = "2026-05-29T10:00:00-06:00_1749000000"
        d_str = date_clicked.split("_")[0]
        # Remove timezone offset if present for datetime-local
        if "+" in d_str: d_str = d_str.split("+")[0]
        # if only date (month view), add time
        if "T" not in d_str:
            start_val = f"{d_str}T08:00"
            end_val = f"{d_str}T09:00"
        else:
            # It's an exact time click in week/day view. Let's make it 1 hour
            start_val = d_str[:16] # truncate seconds/ms
            # simplistic +1 hr logic
            try:
                dt = datetime.strptime(start_val, "%Y-%m-%dT%H:%M")
                end_val = (dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
            except:
                end_val = start_val
        return True, "", start_val, end_val, "", None, "scheduled", False, {"display": "block"}, {"display": "none"}, topics_options, []
            
    if trigger_id == "cal-event-clicked" and event_clicked:
        ev_id = event_clicked.split("_")[0]
        # Find the event in the store
        evt = next((e for e in events if e['id'] == ev_id), None)
        if evt:
            s_val = evt['start'][:16] if evt['start'] else ""
            e_val = evt['end'][:16] if evt['end'] else ""
            
            # Fetch current topics for this appointment
            selected_topics = []
            if token and evt['id']:
                try:
                    apt_res = requests.get(f"{API_URL}/appointments/", headers=headers)
                    if apt_res.status_code == 200:
                        all_apts = apt_res.json()
                        this_apt = next((a for a in all_apts if str(a['id']) == evt['id']), None)
                        if this_apt and 'topics' in this_apt:
                            selected_topics = [t['id'] for t in this_apt['topics']]
                except:
                    pass
            
            return True, evt['id'], s_val, e_val, evt.get('context'), evt.get('case_id'), evt.get('status', 'scheduled'), False, {"display": "none"}, {"display": "block"}, topics_options, selected_topics
            
    return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    Output("apt-error", "children"),
    Output("trigger-reload-calendar", "data"),
    Output("close-modal-trigger", "data"),
    Input("btn-save-apt", "n_clicks"),
    Input("btn-cancel-apt", "n_clicks"),
    State("apt-id", "value"),
    State("apt-start", "value"),
    State("apt-end", "value"),
    State("apt-notes", "value"),
    State("apt-case-id", "value"),
    State("apt-status", "value"),
    State("apt-biweekly-switch", "value"),
    State("apt-topics-checklist", "value"),
    State("auth-token", "data"),
    State("trigger-reload-calendar", "data"),
    prevent_initial_call=True
)
def handle_save_apt(save_click, cancel_click, apt_id, start_time, end_time, notes, case_id, status, is_biweekly, selected_topics, token, reload_trigger):
    ctx = dash.callback_context
    if not ctx.triggered or not token:
        return "", dash.no_update, dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    headers = {"Authorization": f"Bearer {token}"}
    
    if trigger_id == "btn-cancel-apt" and apt_id:
        res = requests.delete(f"{API_URL}/appointments/{apt_id}", headers=headers)
        if res.status_code != 200:
            return f"Error: {res.json().get('detail')}", dash.no_update, dash.no_update
        return "", (reload_trigger or 0) + 1, (reload_trigger or 0) + 1
        
    if trigger_id == "btn-save-apt":
        if apt_id:
            payload = {
                "start_time": start_time,
                "end_time": end_time,
                "notes": notes,
                "status": status
            }
            res = requests.patch(f"{API_URL}/appointments/{apt_id}", json=payload, headers=headers)
        else:
            me_res = requests.get(f"{API_URL}/users/me", headers=headers)
            me = me_res.json()
            payload = {
                "case_id": int(case_id) if case_id else None,
                "start_time": start_time,
                "end_time": end_time,
                "notes": notes,
                "status": status,
                "therapist_id": me.get('id')
            }
            if is_biweekly:
                res = requests.post(f"{API_URL}/appointments/biweekly", json=payload, headers=headers)
            else:
                res = requests.post(f"{API_URL}/appointments/", json=payload, headers=headers)
            
        if res.status_code not in [200, 201]:
            return f"Error: {res.json().get('detail')}", dash.no_update, dash.no_update
            
        # Also update topics if apt_id exists or newly created
        new_apt_id = apt_id or (res.json().get('id') if not is_biweekly else res.json()[0].get('id'))
        if new_apt_id and selected_topics is not None:
            requests.post(f"{API_URL}/appointments/{new_apt_id}/topics", json={"topic_ids": selected_topics}, headers=headers)
            
        return "", (reload_trigger or 0) + 1, (reload_trigger or 0) + 1
        
    return "", dash.no_update, dash.no_update

@callback(
    Output("badge-total", "children"),
    Output("badge-scheduled", "children"),
    Output("badge-completed", "children"),
    Input("cal-events-store", "data"),
    Input("cal-view-range", "value"),
    prevent_initial_call=False
)
def update_counters(events, range_str):
    if not events or not range_str:
        return "Totales: 0", "Programadas: 0", "Completadas: 0"
        
    try:
        range_data = json.loads(range_str)
        # FullCalendar returns ISO strings like 2026-05-24T00:00:00Z
        start_date = datetime.strptime(range_data['start'][:19], "%Y-%m-%dT%H:%M:%S")
        end_date = datetime.strptime(range_data['end'][:19], "%Y-%m-%dT%H:%M:%S")
        
        # Filter events
        total = 0
        scheduled = 0
        completed = 0
        
        for ev in events:
            ev_start = datetime.strptime(ev['start'][:19], "%Y-%m-%dT%H:%M:%S")
            # If the event falls within the current view
            if start_date <= ev_start < end_date:
                total += 1
                if ev.get('status') == 'completed':
                    completed += 1
                elif ev.get('status') == 'scheduled':
                    scheduled += 1
                    
        return f"Totales: {total}", f"Programadas: {scheduled}", f"Completadas: {completed}"
    except Exception as e:
        print("Error parsing range:", e)
        return "Totales: 0", "Programadas: 0", "Completadas: 0"

@callback(
    Output("trigger-reload-calendar", "data", allow_duplicate=True),
    Input("cal-status-quick-change", "value"),
    State("auth-token", "data"),
    State("trigger-reload-calendar", "data"),
    prevent_initial_call=True
)
def handle_quick_status_change(quick_change_val, token, reload_trigger):
    if not quick_change_val or not token:
        return dash.no_update
        
    try:
        data = json.loads(quick_change_val.split("_|ts|_")[0])
        apt_id = data.get("id")
        new_status = data.get("status")
        
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"status": new_status}
        res = requests.patch(f"{API_URL}/appointments/{apt_id}", json=payload, headers=headers)
        
        if res.status_code in [200, 201]:
            return (reload_trigger or 0) + 1
    except Exception as e:
        print("Error changing quick status:", e)
        
    return dash.no_update

# --- Callbacks ---

@callback(
    Output("cases-table", "columns"),
    Output("cases-table", "data"),
    Output("protocol-case-dropdown", "options"),
    Output("single-case-dropdown", "options"),
    Output("apt-case-id", "options"),
    Input("therapist-url", "pathname"),
    State("auth-token", "data")
)
def load_cases_and_dropdown(pathname, token):
    if not token:
        return [], [], [], [], []
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/cases", headers=headers)
        if response.status_code == 200:
            cases = response.json()
            if not cases: return [], [], [], [], []
            df = pd.json_normalize(cases)
            
            # For table
            table_df = df[['id', 'participant.full_name', 'status']].copy()
            table_df.columns = ['ID', 'Paciente', 'Estado']
            table_df['Acciones'] = table_df['ID'].apply(lambda x: f"[Ver/Editar](/patient/{x})")
            
            cols = [{"name": i, "id": i, "presentation": "markdown"} if i == "Acciones" else {"name": i, "id": i} for i in table_df.columns]
            
            # For Dropdown
            opts = [{"label": f"[{c['id']}] {c['participant']['full_name']}", "value": c['id']} for c in cases if c['status'] in ['active', 'assigned']]
            
            return cols, table_df.to_dict('records'), opts, opts, opts
    except Exception as e:
        print("Error cases:", e)
    return [], [], [], [], []

@callback(
    Output("modal-protocol", "is_open"),
    Input("btn-open-protocol", "n_clicks"),
    Input("btn-submit-protocol", "n_clicks"),
    State("protocol-case-dropdown", "value"),
    State("protocol-start-date", "value"),
    State("protocol-start-time", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def handle_protocol_modal(open_btn, submit_btn, case_id, date_str, time_str, token):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id']
    
    if "btn-open-protocol" in trigger:
        return True
        
    if "btn-submit-protocol" in trigger:
        # Generate the multi-schedule
        if case_id and date_str and time_str and token:
            headers = {"Authorization": f"Bearer {token}"}
            start_dt_str = f"{date_str}T{time_str}:00Z"
            payload = {
                "case_id": case_id,
                "start_date": start_dt_str,
                "num_sessions": 14
            }
            res = requests.post(f"{API_URL}/sessions/biweekly", json=payload, headers=headers)
            print("Protocol scheduled:", res.status_code)
        return False
    return False

@callback(
    Output("modal-single", "is_open"),
    Input("btn-add-single", "n_clicks"),
    Input("btn-submit-single", "n_clicks"),
    State("single-case-dropdown", "value"),
    State("single-start-date", "value"),
    State("single-start-time", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def handle_single_modal(open_btn, submit_btn, case_id, date_str, time_str, token):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id']
    
    if "btn-add-single" in trigger:
        return True
        
    if "btn-submit-single" in trigger:
        if case_id and date_str and time_str and token:
            headers = {"Authorization": f"Bearer {token}"}
            start_dt_str = f"{date_str}T{time_str}:00Z"
            try:
                requests.post(f"{API_URL}/cases/{case_id}/sessions", json={"case_id": int(case_id), "session_date": start_dt_str, "modality": "online"}, headers=headers)
            except Exception as e:
                print("Single Error:", e)
        return False

    return False, no_update, no_update, no_update, no_update, no_update, no_update, no_update

@callback(
    Output("session-notify-alert", "children"),
    Output("session-notify-alert", "is_open"),
    Output("session-notify-alert", "color"),
    Input("btn-send-reminder", "n_clicks"),
    State("current-session-id", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def send_reminder_email(n_clicks, session_id, token):
    if not n_clicks or not session_id or not token:
        return no_update, no_update, no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(f"{API_URL}/sessions/{session_id}/remind", headers=headers)
        if res.status_code == 200:
            return "¡Recordatorio enviado exitosamente al paciente!", True, "success"
        else:
            return f"Error al enviar: {res.text}", True, "danger"
    except Exception as e:
        return f"Error de conexión: {str(e)}", True, "danger"

@callback(
    Output("feedback-modal", "is_open", allow_duplicate=True),
    Input("therapist-url", "pathname"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def check_feedback_status_on_load(pathname, token):
    if not token or pathname != "/therapist":
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/users/me/feedback/status", headers=headers)
        if res.status_code == 200:
            data = res.json()
            return not data.get("already_submitted", True)
    except Exception as e:
        print("Error checking feedback status:", e)
    return False

@callback(
    Output("feedback-modal", "is_open"),
    Output("feedback-alert", "children"),
    Output("feedback-alert", "is_open"),
    Input("btn-submit-feedback", "n_clicks"),
    Input("btn-skip-feedback", "n_clicks"),
    State("feedback-q1", "value"),
    State("feedback-q2", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def handle_feedback_submission(submit_clicks, skip_clicks, q1, q2, token):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-skip-feedback":
        return False, "", False
        
    if trigger_id == "btn-submit-feedback" and token:
        if q1 is None or q2 is None:
            return dash.no_update, "Por favor responde ambas preguntas.", True
            
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "q1_score": int(q1),
            "q2_score": int(q2)
        }
        try:
            res = requests.post(f"{API_URL}/users/me/feedback", json=payload, headers=headers)
            if res.status_code in [200, 201]:
                return False, "", False
            else:
                try:
                    detail = res.json().get("detail", res.text)
                except:
                    detail = res.text
                return True, f"Error al guardar: {detail}", True
        except Exception as e:
            return True, f"Error de conexión: {str(e)}", True
            
    return dash.no_update, dash.no_update, dash.no_update

