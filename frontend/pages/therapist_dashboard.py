import dash
from dash import html, dcc, callback, Input, Output, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import requests
import os
from datetime import datetime, timedelta

dash.register_page(__name__, path='/therapist', name='Therapist Dashboard')

API_URL = os.getenv("API_URL", "http://localhost:8000")

layout = dbc.Container([
    dcc.Location(id="therapist-url"),
    dcc.Interval(id="therapist-interval", interval=60000, n_intervals=0), # Auto refresh 1 min
    
    dbc.Row([
        dbc.Col(html.H2("Mi Consultorio 🩺", className="my-4 text-primary"), width=6),
        dbc.Col([
            dbc.Button("📅 Agendar Cita Única", id="btn-add-single", color="outline-primary", className="my-4 float-end mx-2"),
            dbc.Button("🗓️ Iniciar Protocolo Bi-semanal", id="btn-open-protocol", color="primary", className="my-4 float-end")
        ], width=6)
    ]),

    dbc.Row([
        # Calendario Semanal
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Mi Calendario de Sesiones (Próximos 14 días)")),
                dbc.CardBody([
                    dcc.Loading(dcc.Graph(id="calendar-graph", style={"height": "500px"})),
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

    # Modal Sesión Específica (Notas o Cambiar fecha)
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gestor de Cita / Notas Clínicas")),
        dbc.ModalBody([
            dbc.Alert(id="session-notify-alert", is_open=False, color="success"),
            html.H6(id="session-patient-name", className="text-primary"),
            html.P(id="session-date-display", className="text-muted"),
            
            dcc.Store(id="current-session-id"),
            
            dbc.Label("Notas de la Consulta (Aparecerán en el Expediente):"),
            dbc.Textarea(id="session-notes-input", rows=4, className="mb-3"),
            
            dbc.Label("Estado de la Cita:"),
            dbc.Select(id="session-status-select", options=[
                {"label": "Agendada", "value": "scheduled"},
                {"label": "Completada", "value": "completed"},
                {"label": "Cancelada / Falta", "value": "cancelled"}
            ], value="scheduled", className="mb-3"),
            
            dbc.Button("Guardar Registro de Sesión", id="btn-save-session", color="primary", className="w-100")
        ])
    ], id="modal-session-note", is_open=False)

], fluid=True)

# --- Callbacks ---

@callback(
    Output("cases-table", "columns"),
    Output("cases-table", "data"),
    Output("protocol-case-dropdown", "options"),
    Input("therapist-url", "pathname"),
    State("auth-token", "data")
)
def load_cases_and_dropdown(pathname, token):
    if not token:
        return [], [], []
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/cases", headers=headers)
        if response.status_code == 200:
            cases = response.json()
            if not cases: return [], [], []
            df = pd.json_normalize(cases)
            
            # For table
            table_df = df[['id', 'participant.full_name', 'status']].copy()
            table_df.columns = ['ID', 'Paciente', 'Estado']
            table_df['Acciones'] = table_df['ID'].apply(lambda x: f"[Ver/Editar](/patient/{x})")
            
            cols = [{"name": i, "id": i, "presentation": "markdown" if i == "Acciones" else "None"} for i in table_df.columns]
            
            # For Dropdown
            opts = [{"label": f"[{c['id']}] {c['participant']['full_name']}", "value": c['id']} for c in cases if c['status'] in ['active', 'assigned']]
            
            return cols, table_df.to_dict('records'), opts
    except Exception as e:
        print("Error cases:", e)
    return [], [], []

@callback(
    Output("calendar-graph", "figure"),
    Input("therapist-url", "pathname"),
    Input("therapist-interval", "n_intervals"),
    Input("btn-submit-protocol", "n_clicks"), # refresh on submit
    Input("btn-save-session", "n_clicks"),
    State("auth-token", "data")
)
def load_calendar(path, itv, submit_protocol, save_session, token):
    if not token: return {}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Fetch sessions
        s_res = requests.get(f"{API_URL}/sessions/therapist", headers=headers)
        c_res = requests.get(f"{API_URL}/cases", headers=headers)
        
        if s_res.status_code == 200 and c_res.status_code == 200:
            sessions = s_res.json()
            cases = {c['id']: c['participant']['full_name'] for c in c_res.json()}
            
            if not sessions:
                fig = px.scatter(title="Sin citas programadas (Calendario Limpio)")
                fig.update_layout(xaxis_title="Días Calendario", yaxis_title="Horario")
                return fig
                
            df = pd.DataFrame(sessions)
            df['session_date'] = pd.to_datetime(df['session_date'])
            df['date_only'] = df['session_date'].dt.date
            df['hour_only'] = df['session_date'].dt.strftime("%H:%M")
            df['paciente'] = df['case_id'].map(cases)
            
            # Filter only last 7 days and next 30 days
            min_date = datetime.utcnow().date() - timedelta(days=7)
            max_date = datetime.utcnow().date() + timedelta(days=30)
            df = df[(df['date_only'] >= min_date) & (df['date_only'] <= max_date)]
            
            color_map = {"scheduled": "blue", "completed": "green", "cancelled": "red"}
            
            fig = px.scatter(
                df, x="date_only", y="hour_only", 
                color="status", text="paciente",
                color_discrete_map=color_map,
                hover_data=["id", "therapist_notes"],
                title="Agenda de Citas Activas (Próximos Días)",
                size_max=15
            )
            # Make markers larger
            fig.update_traces(marker=dict(size=20), textposition="top center")
            fig.update_layout(
                yaxis=dict(autorange="reversed", type="category", title="Hora de Consulta"),
                xaxis=dict(title="Día"),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            return fig
    except Exception as e:
        print("Calendar erro:", e)
    return {}

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
    Output("modal-session-note", "is_open"),
    Output("current-session-id", "data"),
    Output("session-patient-name", "children"),
    Output("session-date-display", "children"),
    Output("session-notes-input", "value"),
    Output("session-status-select", "value"),
    Input("calendar-graph", "clickData"),
    Input("btn-save-session", "n_clicks"),
    State("auth-token", "data"),
    State("current-session-id", "data"),
    State("session-notes-input", "value"),
    State("session-status-select", "value"),
    prevent_initial_call=True
)
def handle_session_modal(clickData, save_btn, token, current_id, notes, status):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id']
    
    if "calendar-graph" in trigger and clickData:
        # Load up clicked point data
        point = clickData['points'][0]
        s_id = point['customdata'][0] # ID that we mapped in hover_data
        p_name = point['text']
        s_date = f"{point['x']} - {point['y']}"
        s_notes = point['customdata'][1] if len(point['customdata']) > 1 else ""
        
        # Color mapped to status? The user sees 'scheduled' inside the chart color map. Let's just fetch it securely from backend if needed.
        # But we can just default to fetching from REST or trust Plotly state. Plotly state is easiest.
        
        return True, s_id, f"Paciente: {p_name}", f"Agendada: {s_date}", s_notes, no_update
        
    if "btn-save-session" in trigger and current_id:
        # Patch the session note and status
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "session_date": "2026-04-10T10:00Z", # Dummy required by base schema, we should fetch actual date but schemas.SessionBase requires it?
            # Wait, schemas.SessionBase requires session_date to not be optional. We can just send the same date or refactor the PUT endpoint to allow partial updates.
        }
        # For safety, let's fetch the session first to get its date, then PUT the changes.
        try:
            req_get = requests.get(f"{API_URL}/sessions/therapist", headers=headers)
            target = next((s for s in req_get.json() if s['id'] == current_id), None)
            if target:
                payload = {
                    "session_date": target["session_date"],
                    "therapist_notes": notes,
                    "status": status
                }
                requests.put(f"{API_URL}/sessions/{current_id}", json=payload, headers=headers)
        except Exception as e:
            print("Error saving session note:", e)
        
        return False, no_update, "", "", "", no_update
        
    return False, no_update, no_update, no_update, no_update, no_update
