import base64
import io
import dash
from dash import html, dcc, callback, Input, Output, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
import os

dash.register_page(__name__, path='/coordinator', name='Coordinator Dashboard')

API_URL = os.getenv("API_URL", "http://localhost:8000")

layout = dbc.Container([
    dcc.Location(id="coord-url"),
    html.H2("Tablero de Administración Local", id="coord-title", className="my-4"),
    
    dbc.Tabs([
        dbc.Tab(
            dbc.Card([
                dbc.CardBody([
                    dbc.Button("Sugerir Terapeuta (Asignación Inteligente)", id="btn-smart-match", color="primary", className="mb-2 w-100 fw-bold border-dark"),
                    html.Div(id="smart-match-result", className="mb-3 text-center"),
                    dash_table.DataTable(
                        id='waitlist-table',
                        columns=[],
                        data=[],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'column_id': 'Resumen (LimeSurvey)'},
                                'whiteSpace': 'normal',
                                'height': 'auto',
                                'minWidth': '250px'
                            },
                            {
                                'if': {'column_id': 'Palabras de Riesgo'},
                                'whiteSpace': 'normal',
                                'color': 'red',
                                'fontWeight': 'bold'
                            }
                        ],
                        row_selectable='single',
                        markdown_options={"html": True}
                    ),
                    html.Div(id="dummy-container")
                ])
            ], className="border-top-0 border-light mb-4 shadow-sm"),
            label="Lista de Espera"
        ),
        dbc.Tab(
            dbc.Card(dbc.CardBody([
                dbc.Row(className="mb-4 align-items-center", justify="between", children=[
                    dbc.Col(html.H5("Métricas de la Sede", className="mb-0"), width="auto"),
                    dbc.Col(html.Div([
                        html.Span("Ingreso desde/hasta: ", className="me-2 text-muted small"),
                        dcc.DatePickerRange(
                            id='csv-date-range',
                            display_format='YYYY-MM-DD',
                            className="me-3",
                            start_date_placeholder_text="Inicio",
                            end_date_placeholder_text="Fin"
                        ),
                        dbc.Button("Descargar CSV", id="btn-download-csv", color="success", size="sm")
                    ], className="d-flex align-items-center"), width="auto")
                ]),
                dcc.Download(id="download-dataframe-csv"),
                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody([
                        html.H4(id="kpi-unassigned", className="text-primary"),
                        html.P("Pacientes No Asignados", className="text-muted mb-0")
                    ]), className="text-center shadow-sm mb-3"), width=4),
                    dbc.Col(dbc.Card(dbc.CardBody([
                        html.H4(id="kpi-active", className="text-success"),
                        html.P("Consultantes Activos", className="text-muted mb-0")
                    ]), className="text-center shadow-sm mb-3"), width=4),
                    dbc.Col(dbc.Card(dbc.CardBody([
                        html.H4(id="kpi-therapists", className="text-info"),
                        html.P("Terapeutas en Sede", className="text-muted mb-0")
                    ]), className="text-center shadow-sm mb-3"), width=4),
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="site-metrics-pie"), width=12, md=6),
                    dbc.Col([
                        html.H6("Carga de Pacientes por Terapeuta", className="text-center mb-3 mt-4 mt-md-0"),
                        dash_table.DataTable(
                            id='therapists-load-table',
                            columns=[
                                {"name": "Terapeuta", "id": "Terapeuta"}, 
                                {"name": "Asignados (Por Contactar)", "id": "Asignados"},
                                {"name": "Activos (En Sesiones)", "id": "Activos"},
                                {"name": "Total", "id": "Total"}
                            ],
                            data=[],
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'center', 'padding': '10px'},
                            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                        )
                    ], width=12, md=6),
                ])
            ]), className="border-top-0 border-light mb-4 shadow-sm"),
            label="Métricas de la Sede"
        ),
        dbc.Tab(
            dbc.Card(dbc.CardBody([
                html.Div([
                    html.H5("Rendimiento de Terapeutas", className="d-inline-block"),
                    html.Div([
                        dbc.Button("Descargar Reporte Completo", id="btn-download-therapist-conglomerate", color="success", size="sm", className="me-2"),
                        dbc.Button("Editar Directorio", id="btn-open-therapists-modal", color="secondary", size="sm")
                    ], className="float-end")
                ], className="mb-4 w-100"),
                dcc.Dropdown(id="therapist-metrics-dropdown", placeholder="Seleccione un terapeuta..."),
                dcc.Download(id="download-therapist-conglomerate-csv"),
                html.Div(id="therapist-metrics-content", className="mt-4")
            ]), className="border-top-0 border-light mb-4 shadow-sm"),
            label="Métricas de Terapeutas"
        ),
        dbc.Tab(
            dbc.Card(dbc.CardBody([
                html.Div([
                    html.H5("Analíticas de Consultantes Asignados", className="d-inline-block"),
                    html.Div([
                        dbc.Button("Descargar Reporte Completo", id="btn-download-conglomerate", color="success", size="sm", className="me-2"),
                        dbc.Button("Editar Directorio", id="btn-open-consultants-modal", color="secondary", size="sm")
                    ], className="float-end")
                ], className="mb-4 w-100"),
                dcc.Dropdown(id="consultant-metrics-dropdown", placeholder="Seleccione un consultante asignado..."),
                dcc.Download(id="download-conglomerate-csv"),
                html.Div(id="consultant-metrics-content", className="mt-4")
            ]), className="border-top-0 border-light mb-4 shadow-sm"),
            label="Métricas de Consultantes"
        ),
    ]),
    
    # Therapists Directory Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Directorio de Terapeutas")),
        dbc.ModalBody([
            # Bulk Upload Zone
            dcc.Upload(
                id='upload-therapists-data',
                children=html.Div([
                    'Arrastra o ', html.A('Selecciona Archivo Excel/CSV')
                ]),
                style={
                    'width': '100%', 'height': '60px', 'lineHeight': '60px',
                    'borderWidth': '1px', 'borderStyle': 'dashed',
                    'borderRadius': '5px', 'textAlign': 'center', 'margin-bottom': '15px'
                },
                multiple=False
            ),
            dbc.Alert(id="therapist-bulk-alert", is_open=False, duration=5000),
            
            dbc.Alert(id="therapist-save-alert", is_open=False, duration=3000),
            dash_table.DataTable(
                id='therapists-directory-table',
                columns=[
                    {"name": "ID", "id": "id", "editable": False},
                    {"name": "Correo Electrónico", "id": "email", "editable": False},
                    {"name": "Nombre Completo", "id": "full_name", "editable": True},
                    {"name": "Teléfono", "id": "phone", "editable": True},
                    {"name": "Categoría", "id": "therapist_category", "editable": True, "type": "numeric"},
                    {"name": "Activo", "id": "is_active", "editable": True, "presentation": "dropdown"}
                ],
                data=[],
                editable=True,
                dropdown={
                    'is_active': {
                        'options': [
                            {'label': 'Sí', 'value': True},
                            {'label': 'No', 'value': False}
                        ]
                    }
                },
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                style_data={'backgroundColor': 'white', 'color': 'black'} # Ensure text is visible
            ),
            dcc.Download(id="download-therapists-csv")
        ]),
        dbc.ModalFooter([
            dbc.Button("Registrar Nuevo Terapeuta", id="btn-open-add-therapist", color="info", className="me-auto"),
            dbc.Button("Descargar CSV", id="btn-download-therapists", color="success", className="mx-2"),
            dbc.Button("Guardar Cambios", id="btn-save-therapists", color="primary", className="me-2"),
            dbc.Button("Cerrar", id="btn-close-therapists-modal", color="secondary")
        ])
    ], id="therapists-modal", size="xl", is_open=False, autofocus=False),

    # Add Therapist Form Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Registrar Nuevo Terapeuta")),
        dbc.ModalBody([
            dbc.Alert(id="add-therapist-alert", is_open=False, duration=3000),
            dbc.Input(id="add-th-email", type="email", placeholder="Correo Electrónico Institucional (Requerido)", className="mb-3"),
            html.P("Nota: El terapeuta será dado de alta con la contraseña por defecto 'Espora2026!'", className="text-muted small"),
            dbc.Input(id="add-th-name", type="text", placeholder="Nombre Completo (Requerido para gráficas)", className="mb-3"),
            dbc.Input(id="add-th-phone", type="text", placeholder="Teléfono (Opcional)", className="mb-3"),
            dbc.Input(id="add-th-category", type="number", placeholder="Categoría de Terapeuta (Opcional)", className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Crear Terapeuta", id="btn-submit-add-therapist", color="primary", className="me-2"),
            dbc.Button("Cancelar", id="btn-cancel-add-therapist", color="secondary")
        ])
    ], id="add-therapist-modal", is_open=False),

    # Consultants Directory Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Directorio de Consultantes")),
        dbc.ModalBody([
            # Bulk Upload Zone
            dcc.Upload(
                id='upload-consultants-data',
                children=html.Div([
                    'Arrastra o ', html.A('Selecciona Archivo Excel/CSV')
                ]),
                style={
                    'width': '100%', 'height': '60px', 'lineHeight': '60px',
                    'borderWidth': '1px', 'borderStyle': 'dashed',
                    'borderRadius': '5px', 'textAlign': 'center', 'margin-bottom': '15px'
                },
                multiple=False
            ),
            dbc.Alert(id="consultant-bulk-alert", is_open=False, duration=5000),

            dbc.Alert(id="consultant-save-alert", is_open=False, duration=3000),
            dash_table.DataTable(
                id='consultants-directory-table',
                columns=[
                    {"name": "ID Caso", "id": "case_id", "editable": False},
                    {"name": "Nombre Completo", "id": "full_name", "editable": True},
                    {"name": "No. Cuenta", "id": "student_account", "editable": True},
                    {"name": "Correo Electrónico", "id": "email", "editable": True},
                    {"name": "Teléfono", "id": "phone", "editable": True},
                    {"name": "Facultad", "id": "faculty", "editable": True},
                    {"name": "Carrera", "id": "career", "editable": True},
                    {"name": "Terapeuta", "id": "therapist_name", "editable": False},
                    {"name": "Estado", "id": "status", "editable": False},
                    {"name": "Acciones", "id": "acciones", "editable": False, "presentation": "markdown"}
                ],
                data=[],
                editable=True,
                row_selectable='single',
                markdown_options={"html": True},
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                style_data={'backgroundColor': 'white', 'color': 'black'}
            ),
            dcc.Download(id="download-consultants-csv")
        ]),
        dbc.ModalFooter([
            dbc.Button("Añadir Nuevo Consultante", id="btn-open-add-consultant", color="info", className="me-auto"),
            dbc.Button("Descargar CSV", id="btn-download-consultants", color="success", className="mx-2"),
            dbc.Button("Guardar Cambios", id="btn-save-consultants", color="primary", className="me-2"),
            dbc.Button("Cerrar", id="btn-close-consultants-modal", color="secondary")
        ])
    ], id="consultants-modal", size="xl", is_open=False, autofocus=False),
    
    # Add Consultant Form Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Añadir Nuevo Consultante (Asignación Manual)")),
        dbc.ModalBody([
            dbc.Alert(id="add-consultant-alert", is_open=False, duration=3000),
            html.P("Esto creará un nuevo estudiante y lo colocará inmediatamente en la Lista de Espera.", className="text-muted"),
            dbc.Input(id="add-cons-name", type="text", placeholder="Nombre Completo (Requerido)", className="mb-3"),
            dbc.Input(id="add-cons-account", type="text", placeholder="No. Cuenta (Requerido)", className="mb-3"),
            dbc.Input(id="add-cons-email", type="email", placeholder="Correo Electrónico (Requerido)", className="mb-3"),
            dbc.Input(id="add-cons-phone", type="text", placeholder="Teléfono", className="mb-3"),
            dbc.Input(id="add-cons-faculty", type="text", placeholder="Facultad", className="mb-3"),
            dbc.Input(id="add-cons-career", type="text", placeholder="Carrera", className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Crear Consultante", id="btn-submit-add-consultant", color="primary", className="me-2"),
            dbc.Button("Cancelar", id="btn-cancel-add-consultant", color="secondary")
        ])
    ], id="add-consultant-modal", is_open=False),

    # Modal for assignment
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Asignar Terapeuta")),
        dbc.ModalBody([
            html.P(id="assign-case-info"),
            dcc.Dropdown(id="assign-therapist-dropdown", placeholder="Seleccionar terapeuta..."),
            dbc.Alert(id="assign-alert", is_open=False, color="success", className="mt-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="assign-cancel", className="ms-auto", n_clicks=0),
            dbc.Button("Asignar", id="assign-submit", color="primary", n_clicks=0)
        ])
    ], id="assign-modal", is_open=False),
    
    # Dummy store for selected case
    dcc.Store(id="selected-case-id")
])

@callback(
    Output("waitlist-table", "columns"),
    Output("waitlist-table", "data"),
    Input("coord-url", "pathname"),
    Input("assign-modal", "is_open"), # Refresh on close
    State("auth-token", "data"),
    prevent_initial_call=False
)
def load_waitlist(pathname, modal_open, token):
    if not token or modal_open:
        return no_update, no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{API_URL}/cases", headers=headers)
        if response.status_code == 200:
            cases = response.json()
            if not cases:
                return [], []
                
            df = pd.json_normalize(cases)
            
            # Risk Dictionary Logic
            RISK_WORDS = ["suicidio", "morir", "muerte", "ansiedad", "pánico", "desesperanza", "depresión", "lastimar", "cortar", "depresion", "panico"]
            
            def extract_risk_words(text):
                if not isinstance(text, str): return ""
                found_words = []
                lower_text = text.lower()
                for w in RISK_WORDS:
                    if w in lower_text:
                        found_words.append(w.upper())
                return ", ".join(found_words)

            if 'participant.metadata_json.resumen_caso' in df.columns:
                df['Resumen (LimeSurvey)'] = df['participant.metadata_json.resumen_caso'].fillna('Sin resumen')
                df['Palabras de Riesgo'] = df['participant.metadata_json.resumen_caso'].apply(extract_risk_words)
            else:
                df['Resumen (LimeSurvey)'] = 'Sin resumen'
                df['Palabras de Riesgo'] = ''

            # Filter for waiting ONLY for the waitlist table
            waitlist_df = df[df['status'] == 'waiting'].copy()
            if waitlist_df.empty:
                return [], []
                
            waitlist_df = waitlist_df[['id', 'participant.full_name', 'participant.student_account', 'status', 'created_at', 'Resumen (LimeSurvey)', 'Palabras de Riesgo', 'therapist_id']]
            waitlist_df.columns = ['ID Caso', 'Nombre', 'No. Cuenta', 'Estado', 'Fecha Ingreso', 'Resumen (LimeSurvey)', 'Palabras de Riesgo', 'ID Terapeuta']
            
            # Map status to spanish
            status_map = {"waiting": "Lista de Espera", "assigned": "Asignado", "active": "Activo", "closed": "Cerrado"}
            waitlist_df['Estado'] = waitlist_df['Estado'].map(status_map)
            waitlist_df['ID Terapeuta'] = waitlist_df['ID Terapeuta'].fillna("Sin asignar")
            
            # Acciones link to Patient Dashboard
            waitlist_df['Acciones'] = waitlist_df['ID Caso'].apply(lambda x: f"[Ver/Editar](/patient/{x})")
            
            # Set markdown presentation for columns
            columns = [{"name": i, "id": i} for i in waitlist_df.columns]
            for col in columns:
                if col['id'] in ['Resumen (LimeSurvey)', 'Acciones']:
                    col['presentation'] = 'markdown'

            return columns, waitlist_df.to_dict('records')
    except Exception as e:
        print(f"Error cargando datos de espera: {e}")
    
    return [], []

@callback(
    Output("site-metrics-pie", "figure"),
    Output("therapists-load-table", "data"),
    Output("kpi-unassigned", "children"),
    Output("kpi-active", "children"),
    Output("kpi-therapists", "children"),
    Input("coord-url", "pathname"),
    State("auth-token", "data"),
    prevent_initial_call=False
)
def load_site_metrics(pathname, token):
    if not token:
        return go.Figure(), [], "0", "0", "0"
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res_cases = requests.get(f"{API_URL}/cases", headers=headers)
        res_therapists = requests.get(f"{API_URL}/users/therapists", headers=headers)
        
        num_therapists = 0
        therapist_dict = {}
        if res_therapists.status_code == 200:
            therapists = res_therapists.json()
            num_therapists = len(therapists)
            therapist_dict = {float(t['id']): t['email'].split('@')[0].capitalize() for t in therapists}
            
        if res_cases.status_code == 200:
            cases = res_cases.json()
            if not cases:
                return go.Figure(), [], "0", "0", str(num_therapists)
                
            df = pd.json_normalize(cases)
            status_map = {"waiting": "Lista de Espera", "assigned": "Asignado", "active": "Activo", "closed": "Cerrado"}
            df['Estado'] = df['status'].map(status_map)
            df['ID Terapeuta'] = df['therapist_id']
            
            # Use dictionary for mapping, fill anything missing with 'No asignado'
            df['Terapeuta'] = df['ID Terapeuta'].map(therapist_dict).fillna("No asignado")
            
            unassigned_count = len(df[df['status'] == 'waiting'])
            active_count = len(df[df['status'].isin(['active', 'assigned'])])
            
            # Pie chart by status
            status_counts = df['Estado'].value_counts().reset_index()
            status_counts.columns = ['Estado', 'Cantidad']
            pie_fig = px.pie(status_counts, names='Estado', values='Cantidad', title='Distribución de Casos por Estado', hole=0.3)
            
            # Table by therapist (splitting assigned vs active)
            all_therapists_names = list(therapist_dict.values())
            
            assigned_cases = df[df['status'].isin(['assigned', 'active'])]
            if not assigned_cases.empty:
                # Group by therapist and status
                grouped = assigned_cases.groupby(['Terapeuta', 'status']).size().unstack(fill_value=0).reset_index()
                
                # Ensure columns exist even if no cases
                if 'assigned' not in grouped.columns:
                    grouped['assigned'] = 0
                if 'active' not in grouped.columns:
                    grouped['active'] = 0
                    
                grouped = grouped[['Terapeuta', 'assigned', 'active']]
                grouped.columns = ['Terapeuta', 'Asignados', 'Activos']
                
                # Merge with all therapists to ensure 0s are shown
                all_th_df = pd.DataFrame({'Terapeuta': all_therapists_names})
                therapist_counts = pd.merge(all_th_df, grouped, on='Terapeuta', how='left').fillna(0)
                therapist_counts['Asignados'] = therapist_counts['Asignados'].astype(int)
                therapist_counts['Activos'] = therapist_counts['Activos'].astype(int)
                therapist_counts['Total'] = therapist_counts['Asignados'] + therapist_counts['Activos']
            else:
                therapist_counts = pd.DataFrame({'Terapeuta': all_therapists_names, 'Asignados': 0, 'Activos': 0, 'Total': 0})
                
            # Sort by Total descending
            therapist_counts = therapist_counts.sort_values(by="Total", ascending=False)
            table_data = therapist_counts.to_dict('records')
            
            return pie_fig, table_data, str(unassigned_count), str(active_count), str(num_therapists)
    except Exception as e:
        print(f"Error cargando gráficas de sede: {e}")
        
    return go.Figure(), [], "0", "0", "0"

@callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("csv-date-range", "start_date"),
    State("csv-date-range", "end_date"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def download_site_csv(n_clicks, start_date, end_date, token):
    if not token or n_clicks is None:
        return no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        cases_res = requests.get(f"{API_URL}/cases", headers=headers)
        th_res = requests.get(f"{API_URL}/users/therapists", headers=headers)
        
        if cases_res.status_code == 200:
            cases = cases_res.json()
            therapists = th_res.json() if th_res.status_code == 200 else []
            th_dict = {t['id']: t['email'] for t in therapists}
            
            data_export = []
            RISK_WORDS = ["suicidio", "morir", "muerte", "ansiedad", "pánico", "desesperanza", "depresión", "lastimar", "cortar", "depresion", "panico"]
            
            for c in cases:
                created_at = c.get('created_at')
                
                # Check date filters if provided
                if start_date and created_at and created_at < start_date:
                    continue
                if end_date and created_at and created_at > end_date + "T23:59:59":
                    continue
                    
                p = c.get('participant', {})
                meta = p.get('metadata_json', {})
                resumen = meta.get('resumen_caso', '')
                
                found_words = [w.upper() for w in RISK_WORDS if w in resumen.lower()]
                
                th_id = c.get('therapist_id')
                th_email = th_dict.get(th_id, 'No asignado') if th_id else 'No asignado'
                
                data_export.append({
                    "ID Caso": c.get('id'),
                    "Estado": c.get('status'),
                    "Fecha Ingreso": c.get('created_at')[:10] if c.get('created_at') else "",
                    "Nombre": p.get('full_name'),
                    "No. Cuenta": p.get('student_account'),
                    "Email": p.get('email'),
                    "Teléfono": p.get('phone'),
                    "Resumen (LimeSurvey)": resumen,
                    "Palabras de Riesgo": ", ".join(found_words),
                    "Terapeuta Asignado": th_email
                })
            
            df = pd.DataFrame(data_export)
            # Add utf-8-sig encoding for correct Spanish accents display in Excel
            return dcc.send_data_frame(df.to_csv, "casos_sede.csv", index=False, encoding='utf-8-sig')
            
    except Exception as e:
        print(f"Error descargando CSV: {e}")
        
    return no_update

@callback(
    Output("coord-title", "children"),
    Input("coord-url", "pathname"),
    State("auth-token", "data"),
)
def update_title(pathname, token):
    title = "Panel de Coordinación"
    if not token: return title
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        me_res = requests.get(f"{API_URL}/users/me", headers=headers)
        if me_res.status_code == 200:
            site_id = me_res.json().get('site_id')
            if site_id:
                sites_res = requests.get(f"{API_URL}/sites", headers=headers)
                if sites_res.status_code == 200:
                    for s in sites_res.json():
                        if s['id'] == site_id:
                            return f"Panel de Coordinación de {s['name']}"
    except Exception as e:
        print(f"Error cargando titulo: {e}")
@callback(
    Output("therapist-metrics-dropdown", "options"),
    Output("consultant-metrics-dropdown", "options"),
    Input("coord-url", "pathname"),
    State("auth-token", "data"),
    prevent_initial_call=False
)
def load_metrics_dropdowns(pathname, token):
    if not token:
        return [], []
    
    headers = {"Authorization": f"Bearer {token}"}
    therapists = []
    consultants = []
    
    try:
        # Load therapists
        res_t = requests.get(f"{API_URL}/users/therapists", headers=headers)
        if res_t.status_code == 200:
            therapists = [{"label": t["email"], "value": t["id"]} for t in res_t.json()]
            
        # Load assigned/active cases (consultants)
        res_c = requests.get(f"{API_URL}/cases", headers=headers)
        if res_c.status_code == 200:
            cases = res_c.json()
            for c in cases:
                if c["status"] in ["assigned", "active"]:
                    label = f"{c['participant']['full_name']} (Caso #{c['id']})"
                    consultants.append({"label": label, "value": c['id']})
    except Exception as e:
        print(f"Error cargando dropdowns: {e}")
        
    return therapists, consultants

@callback(
    Output("therapist-metrics-content", "children"),
    Input("therapist-metrics-dropdown", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def display_therapist_metrics(therapist_id, token):
    if not token:
        return "Requiere autenticación."
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        me_res = requests.get(f"{API_URL}/users/me", headers=headers)
        if me_res.status_code == 200:
            site_id = me_res.json().get('site_id')
            if not site_id: return "Sede no provista."
            
            stats_res = requests.get(f"{API_URL}/sites/{site_id}/therapist_stats", headers=headers)
            if stats_res.status_code == 200:
                stats = stats_res.json()
                if not stats: return "No existen terapeutas registrados o activos en la sede."
                
                df = pd.DataFrame(stats)
                
                if therapist_id:
                    df = df[df['therapist_id'] == therapist_id]
                    if df.empty: return "El Terapeuta no cuenta con volumen clínico."
                    
                # Figura 1: Carga Laboral
                fig_workload = px.bar(df, x="therapist_name", y="weekly_hours", title="Saturación de Citas Semanales (Horas)", color="weekly_hours", color_continuous_scale="Reds")
                # Figura 2: Demografía
                fig_demo = px.bar(df, x="therapist_name", y=["men", "women"], title="Demografía Anatómica de Pacientes", barmode='group')
                # Figura 3: Casos
                fig_cases = px.bar(df, x="therapist_name", y=["active_cases", "dropouts"], title="Efectividad y Rendimiento (Activos vs Abandonos)", barmode='group')
                
                return dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig_workload), width=12, md=4),
                    dbc.Col(dcc.Graph(figure=fig_demo), width=12, md=4),
                    dbc.Col(dcc.Graph(figure=fig_cases), width=12, md=4)
                ])
                
    except Exception as e:
        print(f"Error loading health metrics: {e}")
        
    return html.Div(f"No se pudieron cargar las analíticas profundas.", className="text-danger mt-3")

@callback(
    Output("smart-match-result", "children"),
    Input("btn-smart-match", "n_clicks"),
    State("waitlist-table", "selected_rows"),
    State("waitlist-table", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def run_smart_matching(n_clicks, selected_rows, data, token):
    if not token: return ""
    if not selected_rows or not data:
        return html.Span("⚠️ Por favor selecciona un alumno de la lista de espera clickeando el círculo a su izquierda.", className="text-danger")
        
    case_student = data[selected_rows[0]]["Nombre"]
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        me_res = requests.get(f"{API_URL}/users/me", headers=headers)
        if me_res.status_code == 200:
            site_id = me_res.json().get('site_id')
            stats_res = requests.get(f"{API_URL}/sites/{site_id}/therapist_stats", headers=headers)
            if stats_res.status_code == 200:
                stats = stats_res.json()
                if not stats: return "No existen datos para emitir recomendación."
                
                # Algoritmo Base: Ordenar por menos horas en semana
                sorted_therapists = sorted(stats, key=lambda x: (x['weekly_hours'], x['active_cases']))
                best_match = sorted_therapists[0]
                
                return html.Div([
                    html.Span("Sugerencia del Motor Matemático: Asignar el paciente "),
                    html.Strong(f"'{case_student}'"),
                    html.Span(" al experto "),
                    html.Strong(f"{best_match['therapist_name']}", className="text-success text-uppercase"),
                    html.Span(f".   Justificación: Mantiene una ocupación horaria semanal sumamente baja ({best_match['weekly_hours']} Hrs) garantizando una absorción segura protegiendo su salud laboral mental.")
                ], className="alert alert-success border-success py-2 mt-2")
    except Exception as e:
        pass
    
    return "No se pudo procesar la asignación."

@callback(
    Output("consultant-metrics-content", "children"),
    Input("consultant-metrics-dropdown", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def display_consultant_metrics(case_id, token):
    if not case_id or not token:
        return "Seleccione un consultante para ver sus detalles."
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/cases", headers=headers)
        if response.status_code == 200:
            cases = response.json()
            case_data = next((c for c in cases if c['id'] == case_id), None)
            
            if not case_data:
                return html.Div("Caso no encontrado.", className="text-danger mt-3")
                
            # Mock risk scores progression
            mock_dates = pd.date_range(start='2026-01-01', periods=5, freq='W')
            mock_scores = [8, 7, 5, 4, 3] # Decreasing risk score over sessions
            
            fig = px.line(x=mock_dates, y=mock_scores, title='Evolución del Nivel de Riesgo (Simulado)', markers=True)
            fig.update_layout(xaxis_title="Fecha de Sesión", yaxis_title="Puntaje de Severidad (0-10)", yaxis_range=[0,10])
            
            resumen = case_data['participant'].get('metadata_json', {}).get('resumen_caso', 'Sin resumen')
            
            return dbc.Row([
                dbc.Col([
                    html.H5(f"Detalles del Consultante: {case_data['participant']['full_name']}"),
                    html.P([html.Strong("No. Cuenta: "), case_data['participant']['student_account']]),
                    html.P([html.Strong("Estado Actual: "), case_data['status'].upper()]),
                    html.Hr(),
                    html.Strong("Resumen LimeSurvey:"),
                    html.P(resumen, className="text-muted mt-2")
                ], width=4),
                dbc.Col([
                    dcc.Graph(figure=fig)
                ], width=8)
            ])
            
    except Exception as e:
        print(f"Error loading consultant metrics: {e}")
        
    return html.Div(f"No se pudo cargar la información para el Caso ID: {case_id}", className="text-danger mt-3")

@callback(
    Output("therapists-directory-table", "data"),
    Input("coord-url", "pathname"),
    Input("add-therapist-modal", "is_open"),
    Input("upload-therapists-data", "contents"),
    State("auth-token", "data"),
    prevent_initial_call=False
)
def load_therapists_directory(pathname, is_add_open, upload_contents, token):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    
    # If the add modal is open, don't refresh yet
    if not token or is_add_open:
        return no_update
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/users/therapists", headers=headers)
        if res.status_code == 200:
            users = res.json()
            # Extract fields for table
            data = []
            for u in users:
                data.append({
                    "id": u["id"],
                    "email": u["email"],
                    "full_name": u.get("full_name", ""),
                    "phone": u.get("phone", ""),
                    "therapist_category": u.get("therapist_category", ""),
                    "is_active": u.get("is_active", True)
                })
            return data
    except Exception as e:
        print(f"Error loading therapists directory: {e}")
    return []

@callback(
    Output("therapist-save-alert", "children"),
    Output("therapist-save-alert", "color"),
    Output("therapist-save-alert", "is_open"),
    Input("btn-save-therapists", "n_clicks"),
    State("therapists-directory-table", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_therapists_directory(n_clicks, table_data, token):
    if not table_data or not token:
        return no_update, no_update, False
        
    headers = {"Authorization": f"Bearer {token}"}
    success_count = 0
    error_count = 0
    
    for row in table_data:
        try:
            update_payload = {
                "full_name": row.get("full_name"),
                "phone": row.get("phone"),
                "therapist_category": row.get("therapist_category"),
                "is_active": row.get("is_active")
            }
            res = requests.put(f"{API_URL}/users/{row['id']}", json=update_payload, headers=headers)
            if res.status_code == 200:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            
    if error_count > 0:
        return f"Actualizados {success_count}, fallaron {error_count}.", "warning", True
        
    return f"¡{success_count} terapeutas actualizados correctamente!", "success", True

@callback(
    Output("download-therapists-csv", "data"),
    Input("btn-download-therapists", "n_clicks"),
    State("therapists-directory-table", "data"),
    prevent_initial_call=True
)
def download_therapists_csv(n_clicks, table_data):
    if not table_data:
        return no_update
        
    df = pd.DataFrame(table_data)
    
    legacy_mapping = {
        'email': 'Email',
        'full_name': 'Nombre Completo',
        'phone': 'Teléfono',
        'therapist_category': 'Categoría',
        'is_active': 'Activo'
    }
    
    df_export = df.rename(columns=legacy_mapping)
    cols_order = ['Email', 'Nombre Completo', 'Teléfono', 'Activo']
    final_cols = [c for c in cols_order if c in df_export.columns] + [c for c in df_export.columns if c not in cols_order and c != 'id']
    
    df_export = df_export[final_cols]
    
    return dcc.send_data_frame(df_export.to_csv, "Directorio_Terapeutas.csv", index=False, encoding='utf-8-sig')

@callback(
    Output("consultants-directory-table", "data"),
    Input("coord-url", "pathname"),
    Input("add-consultant-modal", "is_open"),
    Input("upload-consultants-data", "contents"),
    State("auth-token", "data"),
    prevent_initial_call=False
)
def load_consultants_directory(pathname, is_add_open, upload_contents, token):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # If the add modal is open, don't refresh yet
    if not token or is_add_open:
        return no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Get cases and therapists to map names
        res_cases = requests.get(f"{API_URL}/cases", headers=headers)
        res_th = requests.get(f"{API_URL}/users/therapists", headers=headers)
        
        if res_cases.status_code == 200:
            cases = res_cases.json()
            therapists = res_th.json() if res_th.status_code == 200 else []
            th_dict = {t['id']: t.get('full_name') or t['email'].split('@')[0].capitalize() for t in therapists}
            
            data = []
            for c in cases:
                if c["status"] in ["assigned", "active"]:
                    p = c.get("participant", {})
                    th_name = th_dict.get(c.get("therapist_id"), "Sin asignar")
                    status_map = {"assigned": "Asignado", "active": "Activo"}
                    
                    data.append({
                        "case_id": c["id"],
                        "participant_id": p.get("id"),
                        "full_name": p.get("full_name", ""),
                        "student_account": p.get("student_account", ""),
                        "email": p.get("email", ""),
                        "phone": p.get("phone", ""),
                        "faculty": p.get("faculty", ""),
                        "career": p.get("career", ""),
                        "therapist_name": th_name,
                        "status": status_map.get(c["status"], c["status"]),
                        "acciones": f"[Abrir Expediente](/patient/{c['id']})"
                    })
            return data
    except Exception as e:
        print(f"Error loading consultants directory: {e}")
    return []

@callback(
    Output("consultant-save-alert", "children"),
    Output("consultant-save-alert", "color"),
    Output("consultant-save-alert", "is_open"),
    Input("btn-save-consultants", "n_clicks"),
    State("consultants-directory-table", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def save_consultants_directory(n_clicks, table_data, token):
    if not table_data or not token:
        return no_update, no_update, False
        
    headers = {"Authorization": f"Bearer {token}"}
    success_count = 0
    error_count = 0
    
    for row in table_data:
        try:
            update_payload = {
                "full_name": row.get("full_name"),
                "student_account": row.get("student_account"),
                "email": row.get("email"),
                "phone": row.get("phone"),
                "faculty": row.get("faculty"),
                "career": row.get("career")
            }
            # Put to the new endpoint
            res = requests.put(f"{API_URL}/cases/{row['case_id']}/participant", json=update_payload, headers=headers)
            if res.status_code == 200:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            
    if error_count > 0:
        return f"Actualizados {success_count}, fallaron {error_count}.", "warning", True
        
    return f"¡{success_count} consultantes actualizados correctamente!", "success", True

@callback(
    Output("download-consultants-csv", "data"),
    Input("btn-download-consultants", "n_clicks"),
    State("consultants-directory-table", "data"),
    prevent_initial_call=True
)
def download_consultants_csv(n_clicks, table_data):
    if not table_data:
        return no_update
        
    df = pd.DataFrame(table_data)
    
    # Map to "NUEVA BASE DE DATOS" format if possible
    legacy_mapping = {
        'full_name': 'Nombre del paciente',
        'student_account': 'CURP',
        'email': 'Correo (Interno)',
        'phone': 'Teléfono',
        'faculty': 'Facultad',
        'career': 'Carrera',
        'therapist_name': 'Psicoterapeuta',
        'status': 'Estatus del proceso'
    }
    
    df_export = df.rename(columns=legacy_mapping)
    # Reorder columns to match the legacy format logically
    cols_order = ['Nombre del paciente', 'Psicoterapeuta', 'CURP', 'Correo (Interno)', 'Teléfono', 'Facultad', 'Carrera', 'Estatus del proceso']
    # keep extra columns at the end if they exist
    final_cols = [c for c in cols_order if c in df_export.columns] + [c for c in df_export.columns if c not in cols_order and c != 'case_id']
    
    df_export = df_export[final_cols]
    
    return dcc.send_data_frame(df_export.to_csv, "Directorio_Consultantes.csv", index=False, encoding='utf-8-sig')

@callback(
    Output("download-conglomerate-csv", "data"),
    Input("btn-download-conglomerate", "n_clicks"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def download_conglomerate_csv(n_clicks, token):
    if not token:
        return no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/cases", headers=headers)
        if response.status_code != 200:
            return no_update
            
        cases = response.json()
        df = pd.DataFrame(cases)
        
        # Build a single-row aggregated DataFrame matching the exact 39 columns of Conglomerado
        cols = [
            'Sede', 'Semestre', 'Tipo de sede ', '# total de solicitudes durante el semestre ', 
            '# de solicitudes respondidas (aunque no hayan iniciado proceso psicotrapéutico)', 
            '# de pacientes que se quedaron en lista de espera', '# total de pacientes atendidos en proceso psicoterapéutico', 
            '# de solicitudes de hombres', '# de solicitudes de mujeres ', '# de pacientes atendidos Hombres', 
            '# de pacientes atendidas mujeres ', '# de pacientes que finalizaron tratamiento', 
            '# de pacientes que continúan en tratamiento', '# de interrupciones', '# de abandonos', 
            '# de canalizaciones a psiquiatría ', '# de canalizaciones a otra disciplina', 
            '# de pacientes referidos a proceso a largo plazo (proceso externo)', '# de horas clínicas ', 
            '¿La sede cuenta con API?', '# de personas atendidas por API', '# de horas clínicas del API', 
            '# de pacientes con diagnístico psiquiátrico', '# de internamientos durante el semestre', 
            '# de pac con ideación suicida previa al TX', '# de pac con ideación suicida durante el TX', 
            '# de pac con ideación suicida al finalizar el TX', '# de intentos suicidas durante tratamiento', 
            '# de pacientes con autolesiones ', '# de pacientes que reportan violencia de género', 
            '# de pacientes que reportan violencia sexual', '# de pacientes pertenecientes a las discidencias sexuales ', 
            '# de pacientes con discapacidad ', '# de pacientes con problema de consumo de sustancias ', 
            'Promedio sensación inicial ', 'Promedio ¿qué tanto de ayudó el tratamiento?', 
            'Promedio ¿Cómo te sientes actualmente? ', 'Promedio ¿Qué tanto recomendarías el servicio? ', 
            'Promedio ¿Cómo calificarías la calidad de la atención recibida?'
        ]
        
        agg_data = {col: 0 for col in cols} # Default to 0 / empty
        
        if len(df) > 0:
            total_requests = len(df)
            waiting = len(df[df['status'] == 'WAITING']) if 'status' in df.columns else 0
            in_treatment = len(df[df['status'].isin(['ASSIGNED', 'ACTIVE'])]) if 'status' in df.columns else 0
            finished = len(df[df['status'] == 'CLOSED']) if 'status' in df.columns else 0
            
            agg_data['# total de solicitudes durante el semestre '] = total_requests
            agg_data['# de solicitudes respondidas (aunque no hayan iniciado proceso psicotrapéutico)'] = total_requests - waiting
            agg_data['# de pacientes que se quedaron en lista de espera'] = waiting
            agg_data['# total de pacientes atendidos en proceso psicoterapéutico'] = in_treatment + finished
            agg_data['# de pacientes que continúan en tratamiento'] = in_treatment
            agg_data['# de pacientes que finalizaron tratamiento'] = finished
            
            # Additional Mock Data for demonstration until LimeSurvey sync
            agg_data['# de pacientes atendidos Hombres'] = len(df) // 3
            agg_data['# de pacientes atendidas mujeres '] = len(df) - (len(df) // 3)
            
        agg_df = pd.DataFrame([agg_data])
        return dcc.send_data_frame(agg_df.to_csv, "Conglomerado_Consultantes_ESPORA.csv", index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"Error downloading conglomerate: {e}")
        return no_update

@callback(
    Output("download-therapist-conglomerate-csv", "data"),
    Input("btn-download-therapist-conglomerate", "n_clicks"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def download_therapist_conglomerate_csv(n_clicks, token):
    if not token:
        return no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Fetch both therapists and cases to calculate their workload
        res_t = requests.get(f"{API_URL}/users/therapists", headers=headers)
        res_c = requests.get(f"{API_URL}/cases", headers=headers)
        
        if res_t.status_code != 200 or res_c.status_code != 200:
            return no_update
            
        therapists = res_t.json()
        cases = res_c.json()
        df_cases = pd.DataFrame(cases)
        
        report_data = []
        for t in therapists:
            t_cases = df_cases[df_cases['therapist_id'] == t['id']] if not df_cases.empty and 'therapist_id' in df_cases.columns else pd.DataFrame()
            report_data.append({
                "ID Terapeuta": t['id'],
                "Nombre": t.get('full_name', t.get('email', 'N/A')),
                "Activo": "Sí" if t.get('is_active') else "No",
                "Total Casos Asignados (Histórico)": len(t_cases),
                "Casos Activos": len(t_cases[t_cases['status'] == 'ACTIVE']) if not t_cases.empty and 'status' in t_cases.columns else 0,
                "Casos Finalizados": len(t_cases[t_cases['status'] == 'CLOSED']) if not t_cases.empty and 'status' in t_cases.columns else 0
            })
            
        if not report_data:
            report_data.append({"Mensaje": "No hay terapeutas registrados."})
            
        df_report = pd.DataFrame(report_data)
        return dcc.send_data_frame(df_report.to_csv, "Conglomerado_Terapeutas_ESPORA.csv", index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"Error downloading therapist conglomerate: {e}")
        return no_update

@callback(
    Output("assign-modal", "is_open"),
    Output("selected-case-id", "data"),
    Output("assign-case-info", "children"),
    Output("assign-therapist-dropdown", "options"),
    Output("waitlist-table", "selected_rows"),
    Output("consultants-directory-table", "selected_rows"),
    Input("waitlist-table", "selected_rows"),
    Input("consultants-directory-table", "selected_rows"),
    Input("assign-cancel", "n_clicks"),
    Input("assign-submit", "n_clicks"),
    State("waitlist-table", "data"),
    State("consultants-directory-table", "data"),
    State("auth-token", "data"),
    State("assign-modal", "is_open"),
    State("assign-therapist-dropdown", "value"),
    State("selected-case-id", "data")
)
def handle_modal(wl_rows, cons_rows, btn_cancel, btn_submit, wl_data, cons_data, token, is_open, therapist_id, selected_case_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, no_update, no_update, no_update, no_update, no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    headers = {"Authorization": f"Bearer {token}"}

    if trigger_id in ["waitlist-table", "consultants-directory-table"]:
        if trigger_id == "waitlist-table" and wl_rows:
            case_row = wl_data[wl_rows[0]]
            case_id = case_row['ID Caso']
            name_label = case_row['Nombre']
        elif trigger_id == "consultants-directory-table" and cons_rows:
            case_row = cons_data[cons_rows[0]]
            case_id = case_row['case_id']
            name_label = case_row['full_name']
        else:
            return is_open, no_update, no_update, no_update, no_update, no_update
        
        therapists_opts = []
        try:
            res_t = requests.get(f"{API_URL}/users/therapists", headers=headers)
            res_c = requests.get(f"{API_URL}/cases", headers=headers)
            
            if res_t.status_code == 200 and res_c.status_code == 200:
                therapists = res_t.json()
                cases = res_c.json()
                
                load_dict = {t['id']: 0 for t in therapists}
                for c in cases:
                    th_id = c.get('therapist_id')
                    status = c.get('status')
                    if th_id in load_dict and status in ['assigned', 'active']:
                        load_dict[th_id] += 1
                        
                for t in therapists:
                    name = t['email'].split('@')[0].capitalize()
                    load = load_dict.get(t['id'], 0)
                    label = f"{name} ({load} consultantes activos/asignados)"
                    therapists_opts.append({"label": label, "value": t["id"]})
        except:
            pass
            
        return True, case_id, f"Asignando/Reasignando terapeuta para el caso #{case_id} ({name_label})", therapists_opts, no_update, no_update
        
    if trigger_id == "assign-cancel":
        return False, no_update, no_update, no_update, [], []
        
    if trigger_id == "assign-submit" and therapist_id:
        case_id = selected_case_data
        if not case_id:
            case_id = ctx.states.get("selected-case-id.data")
        try:
            requests.put(
                f"{API_URL}/cases/{case_id}", 
                json={"therapist_id": therapist_id, "status": "assigned"},
                headers=headers
            )
            return False, no_update, no_update, no_update, [], []
        except Exception as e:
            print(f"Error assigning: {e}")
            
    return is_open, no_update, no_update, no_update, no_update, no_update

@callback(
    Output("therapists-modal", "is_open"),
    [Input("btn-open-therapists-modal", "n_clicks"), Input("btn-close-therapists-modal", "n_clicks")],
    [State("therapists-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_therapists_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("consultants-modal", "is_open"),
    [Input("btn-open-consultants-modal", "n_clicks"), Input("btn-close-consultants-modal", "n_clicks")],
    [State("consultants-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_consultants_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# --- Add Therapist Callbacks ---
@callback(
    Output("add-therapist-modal", "is_open"),
    [Input("btn-open-add-therapist", "n_clicks"), Input("btn-cancel-add-therapist", "n_clicks")],
    [State("add-therapist-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_add_therapist_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("add-therapist-alert", "children"),
    Output("add-therapist-alert", "color"),
    Output("add-therapist-alert", "is_open"),
    Input("btn-submit-add-therapist", "n_clicks"),
    State("add-th-email", "value"),
    State("add-th-name", "value"),
    State("add-th-phone", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def submit_new_therapist(n_clicks, email, name, phone, token):
    if not email:
        return "El correo electrónico es estrictamente obligatorio.", "danger", True
        
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "email": email,
        "full_name": name,
        "phone": phone
    }
    
    try:
        res = requests.post(f"{API_URL}/users/therapists/quick", json=payload, headers=headers)
        if res.status_code == 200:
            return "¡Terapeuta creado con éxito! Cierra esta ventana para ver los cambios.", "success", True
        else:
            return f"Error: {res.json().get('detail', 'Desconocido')}", "danger", True
    except Exception as e:
        return f"Error de conexión: {e}", "danger", True

# --- Add Consultant Callbacks ---
@callback(
    Output("add-consultant-modal", "is_open"),
    [Input("btn-open-add-consultant", "n_clicks"), Input("btn-cancel-add-consultant", "n_clicks")],
    [State("add-consultant-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_add_consultant_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@callback(
    Output("add-consultant-alert", "children"),
    Output("add-consultant-alert", "color"),
    Output("add-consultant-alert", "is_open"),
    Input("btn-submit-add-consultant", "n_clicks"),
    State("add-cons-name", "value"),
    State("add-cons-account", "value"),
    State("add-cons-email", "value"),
    State("add-cons-phone", "value"),
    State("add-cons-faculty", "value"),
    State("add-cons-career", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def submit_new_consultant(n_clicks, name, account, email, phone, faculty, career, token):
    if not name or not account or not email:
        return "Nombre, No. Cuenta y Correo son obligatorios.", "danger", True
        
    headers = {"Authorization": f"Bearer {token}"}
    
    # We must fetch the user's site_id to inject into the payload
    try:
        me_res = requests.get(f"{API_URL}/users/me", headers=headers)
        if me_res.status_code != 200:
            return "Error obteniendo sede del coordinador.", "danger", True
            
        site_id = me_res.json().get('site_id')
        
        payload = {
            "full_name": name,
            "student_account": account,
            "email": email,
            "phone": phone,
            "faculty": faculty,
            "career": career,
            "site_id": site_id
        }
        
        res = requests.post(f"{API_URL}/cases/manual", json=payload, headers=headers)
        if res.status_code == 200:
            return "¡Consultante creado e ingresado a Lista de Espera con éxito!", "success", True
        else:
            return f"Error: {res.json().get('detail', 'Desconocido')}", "danger", True
    except Exception as e:
        return f"Error de conexión: {e}", "danger", True

# --- Bulk Upload Callbacks ---
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None
        return df
    except Exception as e:
        print(f"Error parsing file: {e}")
        return None

@callback(
    Output("therapist-bulk-alert", "children"),
    Output("therapist-bulk-alert", "color"),
    Output("therapist-bulk-alert", "is_open"),
    Input("upload-therapists-data", "contents"),
    State("upload-therapists-data", "filename"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def bulk_upload_therapists(contents, filename, token):
    if not contents or not token:
        return no_update, no_update, False
        
    df = parse_contents(contents, filename)
    if df is None:
        return "Error al parsear el archivo. Asegúrate de usar Excel o CSV.", "danger", True
        
    # Standardize expected columns internally (email, password, full_name, phone)
    required_cols = ['email', 'password']
    if not all(col in df.columns for col in required_cols):
        return f"El archivo debe contener las columnas: {', '.join(required_cols)}", "danger", True
        
    payloads = []
    for _, row in df.iterrows():
        payloads.append({
            "email": str(row['email']),
            "password": str(row['password']),
            "role": "therapist",
            "full_name": str(row.get('full_name', '')),
            "phone": str(row.get('phone', ''))
        })
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(f"{API_URL}/users/bulk", json=payloads, headers=headers)
        if res.status_code == 200:
            data = res.json()
            succ = data.get("success_count", 0)
            errs = data.get("errors", [])
            msg = f"¡{succ} terapeutas cargados exitosamente!"
            if errs:
                msg += f" Ocurrieron {len(errs)} errores (revísalos en consola/logs)."
                print("Bulk Upload Errors:", errs)
            return msg, "success" if not errs else "warning", True
        else:
            return f"Error del servidor: {res.text}", "danger", True
    except Exception as e:
        return f"Error de conexión: {e}", "danger", True

@callback(
    Output("consultant-bulk-alert", "children"),
    Output("consultant-bulk-alert", "color"),
    Output("consultant-bulk-alert", "is_open"),
    Input("upload-consultants-data", "contents"),
    State("upload-consultants-data", "filename"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def bulk_upload_consultants(contents, filename, token):
    if not contents or not token:
        return no_update, no_update, False
        
    df = parse_contents(contents, filename)
    if df is None:
        return "Error al parsear el archivo. Asegúrate de usar Excel o CSV.", "danger", True
        
    # Support the old "NUEVA BASE DE DATOS PREPAS.xlsx" format or our standard one.
    # We will look for "Nombre del paciente" or "full_name"
    col_name = None
    if 'Nombre del paciente' in df.columns:
        col_name = 'Nombre del paciente'
    elif 'full_name' in df.columns:
        col_name = 'full_name'
        
    if not col_name:
        return f"El archivo debe contener la columna 'Nombre del paciente' o 'full_name'", "danger", True

    col_account = 'student_account'
    if 'CURP' in df.columns:
        col_account = 'CURP'
    elif 'FOLIO' in df.columns:
        col_account = 'FOLIO'

    col_email = 'email'
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        me_res = requests.get(f"{API_URL}/users/me", headers=headers)
        if me_res.status_code != 200:
            return "Error obteniendo sede del coordinador.", "danger", True
        site_id = me_res.json().get('site_id')
        
        payloads = []
        for _, row in df.iterrows():
            # Skip empty rows where name is missing
            raw_name = str(row[col_name]).strip()
            if not raw_name or raw_name.lower() == 'nan':
                continue
                
            account_val = str(row.get(col_account, 'S/N')).strip()
            email_val = str(row.get(col_email, f"sincorreo_{account_val}@espora.unam.mx")).strip()
            if email_val.lower() == 'nan':
                email_val = f"sincorreo_{account_val}@espora.unam.mx"
                
            payloads.append({
                "full_name": raw_name,
                "student_account": account_val,
                "email": email_val,
                "phone": str(row.get('phone', str(row.get('Teléfono', '')))),
                "faculty": str(row.get('faculty', str(row.get('Facultad', '')))),
                "career": str(row.get('career', str(row.get('Carrera', '')))),
                "site_id": site_id
            })
            
        res = requests.post(f"{API_URL}/cases/bulk", json=payloads, headers=headers)
        if res.status_code == 200:
            data = res.json()
            succ = data.get("success_count", 0)
            errs = data.get("errors", [])
            msg = f"¡{succ} consultantes creados e ingresados a Lista de Espera!"
            if errs:
                msg += f" Ocurrieron {len(errs)} errores (revísalos en consola/logs)."
                print("Bulk Upload Errors:", errs)
            return msg, "success" if not errs else "warning", True
        else:
            return f"Error del servidor: {res.text}", "danger", True
    except Exception as e:
        return f"Error de conexión: {e}", "danger", True
