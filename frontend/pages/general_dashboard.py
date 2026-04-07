import dash
from dash import html, dcc, callback, Input, Output, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import requests
import os

dash.register_page(__name__, path='/general', name='General Dashboard')

API_URL = os.getenv("API_URL", "http://localhost:8000")

layout = dbc.Container([
    dcc.Interval(id='global-metrics-interval', interval=60000, n_intervals=0), # Refresh 1 min
    
    dbc.Row([
        dbc.Col(html.H2("Coordinación General", className="my-4 text-primary"), width=7),
        dbc.Col([
            dbc.Button("Descargar Base de Datos (CSV)", id="btn-download-csv", color="info", className="my-4 float-end"),
            dbc.Button("Crear Nueva Sede", id="btn-open-create-site", color="primary", className="my-4 float-end mx-2 fw-bold")
        ], width=5)
    ]),
    dcc.Download(id="download-data-csv"),
    
    # KPIs Top Row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Total de Solicitudes", className="text-muted"),
                html.H3(id="kpi-total-cases", children="-")
            ])
        ], className="border-primary shadow-sm"), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("En Lista de Espera Global", className="text-muted"),
                html.H3(id="kpi-waiting-cases", children="-", className="text-warning")
            ])
        ], className="border-warning shadow-sm"), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Activos / En Terapia", className="text-muted"),
                html.H3(id="kpi-active-cases", children="-", className="text-success")
            ])
        ], className="border-success shadow-sm"), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Alertas Detonadas", className="text-muted"),
                html.H3(id="kpi-active-alerts", children="-", className="text-danger")
            ])
        ], className="border-danger shadow-sm"), width=3)
    ], className="mb-4"),

    # Main Analytics Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(dbc.Row([
                    dbc.Col("Evolución Histórica de Pacientes"),
                    dbc.Col(
                        dbc.Select(id="site-selector", options=[{"label": "Todas (Global)", "value": "ALL"}], value="ALL", size="sm"), 
                        width="auto"
                    )
                ])),
                dbc.CardBody(dcc.Loading(dcc.Graph(id="global-time-series", style={"height": "350px"})))
            ], className="shadow-sm mb-4")
        ], width=12, lg=7),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(dbc.Row([
                    dbc.Col(html.Span("Mapa de Calor de Indicadores Clave")),
                    dbc.Col(dbc.Button("Alertas", id="btn-open-alerts", size="sm", color="secondary", className="float-end"), width="auto")
                ])),
                dbc.CardBody([
                    dcc.Loading(dcc.Graph(id="global-site-heatmap", style={"height": "350px"})),
                    html.Div(id="heatmap-drilldown-content", className="mt-3 text-muted small") # Zona para mostrar el clic
                ])
            ], className="shadow-sm mb-4")
        ], width=12, lg=5)
    ]),

    # Directorio de Coordinadores Locales
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(dbc.Row([
                    dbc.Col(html.H5("Directorio de Coordinadores de Sede")),
                    dbc.Col(dbc.Button("Dar de Alta Coordinador", id="btn-open-add-coordinator", color="primary", size="sm", className="float-end"), width="auto")
                ])),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='coordinators-directory-table',
                        columns=[
                            {"name": "ID", "id": "id"},
                            {"name": "Nombre", "id": "full_name"},
                            {"name": "Correo Electrónico", "id": "email"},
                            {"name": "Sede / Facultad", "id": "site_name"},
                            {"name": "Estatus", "id": "is_active"}
                        ],
                        data=[],
                        style_table={'overflowX': 'auto', 'minHeight': '150px'},
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                        style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                        style_data_conditional=[{
                            'if': {'filter_query': '{is_active} = "Inactivo"'},
                            'backgroundColor': '#ffe6e6',
                            'color': 'red'
                        }]
                    )
                ])
            ], className="shadow-sm mb-4 border-primary")
        ], width=12)
    ]),

    # Alerts Setting Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Configuración de Alertas")),
        dbc.ModalBody([
            html.P("Elige un parámetro para monitorear en tiempo real todas las sedes:", className="text-muted"),
            dbc.Row([
                dbc.Col(dbc.Select(id="alert-metric", options=[
                    {"label": "Tamaño de Lista de Espera", "value": "waitlist_size"},
                    {"label": "Casos Activos Simultáneos", "value": "active_cases"}
                ], value="waitlist_size"), width=5),
                dbc.Col(dbc.Select(id="alert-operator", options=[
                    {"label": "Mayor que (>)", "value": ">"},
                    {"label": "Igual a (==)", "value": "=="}
                ], value=">"), width=3),
                dbc.Col(dbc.Input(id="alert-threshold", type="number", value=15), width=4)
            ], className="mb-3"),
            dbc.Button("Añadir Regla", id="btn-add-alert", color="primary", className="w-100"),
            html.Hr(),
            html.H6("Reglas Activas"),
            html.Div(id="active-alert-rules-list")
        ])
    ], id="alerts-config-modal", is_open=False, size="lg"),

    # Audit Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Registro de Auditoría de Expedientes")),
        dbc.ModalBody([
            html.P("Registro en tiempo real sobre toda manipulación a los expedientes clínicos del sistema ESPORA.", className="text-muted"),
            dcc.Loading(dash_table.DataTable(
                id="audit-table",
                columns=[
                    {"name": "Fecha", "id": "Fecha"},
                    {"name": "Usuario Responsable", "id": "Usuario"},
                    {"name": "Expediente / Paciente", "id": "Paciente"},
                    {"name": "Campo Alterado", "id": "Campo"},
                    {"name": "Valor Original", "id": "Valor Anterior"},
                    {"name": "Alteración Dictaminada", "id": "Nuevo Valor"}
                ],
                style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '12px', 'minWidth': '100px'},
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                page_size=12,
                sort_action="native",
                filter_action="native",
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9'
                    }
                ]
            ))
        ])
    ], id="audit-modal", is_open=False, size="xl"),
    
    # Create Site Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Registro de Nueva Sede")),
        dbc.ModalBody([
            html.P("Ingrese los datos para registrar una nueva Sede o Facultad institucional.", className="text-muted small"),
            dbc.Label("Nombre Oficial de la Sede/Facultad:"),
            dbc.Input(id="new-site-name", placeholder="Ej. FES Aragón", className="mb-3"),
            dbc.Label("Campos Clínicos Requeridos para esta Sede:"),
            dbc.Checklist(
                id="new-site-dynamic-fields",
                options=[
                    {"label": "Diagnóstico DSM-V / CIE-11", "value": "dsm_v"},
                    {"label": "Nivel de Riesgo Suicida (0-10)", "value": "suicide_risk"},
                    {"label": "Clínica de Derivación", "value": "imss_clinic"},
                    {"label": "Consentimiento Informado Firmado", "value": "informed_consent"}
                ],
                value=["suicide_risk"],
                inline=False,
                className="mb-3 text-secondary"
            ),
            dbc.Alert(id="create-site-alert", is_open=False, duration=4000)
        ]),
        dbc.ModalFooter([
            dbc.Button("Guardar Sede", id="btn-submit-create-site", color="primary", className="ms-auto fw-bold"),
            dbc.Button("Cancelar", id="btn-cancel-create-site", color="secondary", outline=True)
        ])
    ], id="create-site-modal", is_open=False, size="lg"),
    
    # Create Coordinator Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Alta de Coordinador Local")),
        dbc.ModalBody([
            html.P("El usuario se creará con la contraseña temporal genérica 'AdminEspora26!'.", className="text-muted small"),
            dbc.Alert(id="add-coordinator-alert", is_open=False, duration=3000),
            dbc.Label("Correo Electrónico Institucional:"),
            dbc.Input(id="add-coord-email", type="email", placeholder="ejemplo@unam.mx", className="mb-3"),
            dbc.Label("Nombre Completo:"),
            dbc.Input(id="add-coord-name", type="text", placeholder="Lic. Juan Pérez", className="mb-3"),
            dbc.Label("Seleccionar Sede a Administrar (Debe existir previamente):"),
            dcc.Dropdown(id="add-coord-site-dropdown", placeholder="Facultad o Sede...", className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Registrar Coordinador", id="btn-submit-add-coordinator", color="success", className="ms-auto fw-bold"),
            dbc.Button("Cancelar", id="btn-cancel-add-coordinator", color="secondary", outline=True)
        ])
    ], id="add-coordinator-modal", is_open=False, size="lg"),
    
    # Footer discreto
    html.Hr(className="mt-5"),
    dbc.Row([
        dbc.Col(html.Span("ESPORA © 2026", className="text-muted small"), width=10),
        dbc.Col(dbc.Button("Registro de Auditoría", id="btn-open-audit", color="light", outline=True, size="sm", className="float-end text-muted border-0"), width=2)
    ], className="mb-4")

], fluid=True)

@callback(
    Output("kpi-total-cases", "children"),
    Output("kpi-waiting-cases", "children"),
    Output("kpi-active-cases", "children"),
    Output("kpi-active-alerts", "children"),
    Output("global-time-series", "figure"),
    Output("global-site-heatmap", "figure"),
    Output("site-selector", "options"),
    Input("global-metrics-interval", "n_intervals"),
    Input("site-selector", "value"),
    State("auth-token", "data")
)
def update_global_dashboard(n_intervals, selected_site, token):
    if not token:
        return "-", "-", "-", "-", {}, {}, [{"label": "Todas (Global)", "value": "ALL"}]
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/globals/metrics", headers=headers)
        if res.status_code == 200:
            data = res.json()
            
            site_stats = pd.DataFrame(data.get("site_stats", []))
            time_series = pd.DataFrame(data.get("time_series", []))
            alerts = data.get("active_alerts", [])
            
            options_dropdown = [{"label": "Todas (Global)", "value": "ALL"}]
            if not site_stats.empty:
                unique_sites = sorted(site_stats["site"].unique())
                options_dropdown.extend([{"label": s, "value": s} for s in unique_sites])
            
            # Simple KPIs
            total_cases = site_stats["count"].sum() if not site_stats.empty else 0
            waiting = site_stats[site_stats["status"] == "waiting"]["count"].sum() if not site_stats.empty else 0
            active = site_stats[site_stats["status"] == "active"]["count"].sum() if not site_stats.empty else 0
            
            # Time Series Figure
            fig_time = {}
            if not time_series.empty:
                filtered_ts = time_series.copy()
                title_ts = "Evolución Semestral - Global"
                if selected_site and selected_site != "ALL":
                    filtered_ts = filtered_ts[filtered_ts["site"] == selected_site]
                    title_ts = f"Evolución Semestral - {selected_site}"
                
                if not filtered_ts.empty:
                    # Map to binary statuses for clear distinction
                    status_map_series = {"waiting": "En Espera (Sin Asignar)", "assigned": "En Terapia / Atendidos", "active": "En Terapia / Atendidos", "closed": "En Terapia / Atendidos", "cancelled": "Cancelados"}
                    filtered_ts["Estado"] = filtered_ts["status"].map(status_map_series)
                    
                    # Group by month and Estado
                    ts_grouped = filtered_ts.groupby(["month", "Estado"])["count"].sum().reset_index()
                    
                    # Compute explicitly the Total per month line
                    total_monthly = filtered_ts.groupby("month")["count"].sum().reset_index()
                    total_monthly["Estado"] = "Total (Solicitudes Historicas)"
                    
                    # Combine original separated + Total line
                    ts_grouped = pd.concat([ts_grouped, total_monthly], ignore_index=True)
                    ts_grouped = ts_grouped.sort_values(by="month")
                    
                    # Compute a 6 month window
                    now = pd.Timestamp.now()
                    six_months_ago = now - pd.DateOffset(months=6)

                    # Create multiline graph
                    color_discrete_map = {
                        "Total (Solicitudes Historicas)": "black",
                        "En Espera (Sin Asignar)": "red", 
                        "En Terapia / Atendidos": "blue", 
                        "Cancelados": "grey"
                    }
                    
                    fig_time = px.line(ts_grouped, x="month", y="count", color="Estado", title=title_ts, markers=True, color_discrete_map=color_discrete_map)
                    fig_time.update_layout(
                        margin=dict(l=20, r=20, t=30, b=20), 
                        xaxis_title="Mes Calendario", 
                        yaxis_title="Volumen Acumulado",
                        legend_title="Selecciona cuáles visualizar (Clic)"
                    )
                    # Set the initial viewport to 6 months explicitly
                    fig_time.update_xaxes(range=[six_months_ago.strftime("%Y-%m-01"), now.strftime("%Y-%m-%d")])
                
            # Heatmap Matrix for sites
            fig_site = {}
            if not site_stats.empty:
                site_pivot = site_stats.pivot_table(index="site", columns="status", values="count", aggfunc="sum").fillna(0).reset_index()
                site_pivot = site_pivot.set_index("site")
                
                # Crear indice de 'Stress' para ordenar las sedes mas rojas arriba
                # Penalizamos más los que estan 'waiting'
                site_pivot["Total Stress"] = site_pivot.get("waiting", 0) * 2 + site_pivot.get("active", 0)
                site_pivot = site_pivot.sort_values(by="Total Stress", ascending=False)
                site_pivot = site_pivot.drop(columns=["Total Stress", "draft"], errors="ignore")
                
                # Renombrar estatus crudos a KPIs Gerenciales
                site_pivot.rename(columns={
                    "waiting": "Espera Crítica",
                    "active": "Densidad de Consulta",
                    "cancelled": "Bajas / Abandono",
                    "closed": "Casos de Éxito",
                    "assigned": "Recién Asignados"
                }, inplace=True)
                
                fig_site = px.imshow(site_pivot, text_auto=True, aspect="auto", color_continuous_scale="Reds")
                fig_site.update_layout(
                    title="Densidad Clínica por Sede", 
                    margin=dict(l=20, r=20, t=40, b=20),
                    coloraxis_showscale=False
                )
                
            return f"{total_cases:,}", f"{waiting:,}", f"{active:,}", str(len(alerts)), fig_time, fig_site, options_dropdown
            
    except Exception as e:
        print("Error fetching global metrics:", e)
        
    return "-", "-", "-", "-", {}, {}, [{"label": "Todas (Global)", "value": "ALL"}]

@callback(
    Output("alerts-config-modal", "is_open"),
    [Input("btn-open-alerts", "n_clicks")],
    [State("alerts-config-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_alerts_modal(n, is_open):
    return not is_open

@callback(
    Output("download-data-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def download_research_csv(n, token):
    if not token or not n:
        return no_update
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{API_URL}/globals/export/data", headers=headers)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            return dcc.send_data_frame(df.to_csv, "ESPORA_Investigacion_Total.csv", index=False, encoding='utf-8-sig')
    except Exception as e:
        print("CSV Export failed:", e)
        
    return no_update

@callback(
    Output("audit-modal", "is_open"),
    Output("audit-table", "data"),
    Input("btn-open-audit", "n_clicks"),
    State("audit-modal", "is_open"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def toggle_audit_modal(n, is_open, token):
    if not token or not n:
        return is_open, []
        
    if not is_open:
        # Fetch audit records strictly when opening the modal
        headers = {"Authorization": f"Bearer {token}"}
        try:
            res = requests.get(f"{API_URL}/globals/audit_logs", headers=headers)
            if res.status_code == 200:
                data = res.json()
                return True, data
        except Exception as e:
            print("Audit fetch error", e)
    
    return not is_open, no_update

@callback(
    Output("heatmap-drilldown-content", "children"),
    Input("global-site-heatmap", "clickData"),
    prevent_initial_call=True
)
def display_heatmap_drilldown(clickData):
    if not clickData:
        return ""
        
    try:
        point = clickData['points'][0]
        sede = point.get('y')
        kpi = point.get('x')
        valor = point.get('z')
        
        return html.Div([
            html.Strong("🔎 Inspección de Nivel: "),
            html.Span("Sede "),
            html.Strong(sede, className="text-primary"),
            html.Span(" en el rubro "),
            html.Strong(kpi, className="text-info"),
            html.Span(f" ({valor} registros)."),
            html.Hr(className="my-2"),
            dbc.ButtonGroup([
                html.A(dbc.Button(f"🏦 Abrir Panel de {sede}", color="primary", size="sm", className="me-2"), href=f"/sede_analytics?sede={sede}", target="_blank"),
                html.A(dbc.Button(f"📊 Análisis Nacional de {kpi}", color="secondary", outline=True, size="sm"), href=f"/kpi_analytics?kpi={kpi}", target="_blank")
            ], className="d-flex w-100")
        ], className="alert alert-secondary py-2")
        
    except Exception as e:
        return ""

@callback(
    Output("create-site-modal", "is_open"),
    [Input("btn-open-create-site", "n_clicks"), Input("btn-cancel-create-site", "n_clicks")],
    [State("create-site-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_create_site_modal(n1, n2, is_open):
    return not is_open

@callback(
    Output("create-site-alert", "children"),
    Output("create-site-alert", "color"),
    Output("create-site-alert", "is_open"),
    Input("btn-submit-create-site", "n_clicks"),
    State("new-site-name", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def create_site_submit(n, name, token):
    if not name:
        return "Debe ingresar el nombre de la sede.", "warning", True
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(f"{API_URL}/sites/", json={"name": name, "city": "CDMX", "address": "UNAM"}, headers=headers)
        if res.status_code == 200:
            return f"Sede '{name}' operando correctamente.", "success", True
        else:
            return f"Error: {res.json().get('detail')}", "danger", True
    except Exception as e:
        return f"Conexión perdida: {e}", "danger", True

@callback(
    Output("coordinators-directory-table", "data"),
    Output("add-coord-site-dropdown", "options"),
    Input("global-metrics-interval", "n_intervals"),
    Input("add-coordinator-modal", "is_open"), # Refresh when modal closes
    State("auth-token", "data")
)
def load_coordinators_dir(n_intervals, modal_open, token):
    if not token: return [], []
    
    headers = {"Authorization": f"Bearer {token}"}
    table_data = []
    site_options = []
    
    try:
        # Get Sites
        res_sites = requests.get(f"{API_URL}/sites/", headers=headers)
        if res_sites.status_code == 200:
            sites = res_sites.json()
            site_map = {s['id']: s['name'] for s in sites}
            site_options = [{"label": f"ID {s['id']} - {s['name']}", "value": s['id']} for s in sites]
            
            # Get Users
            res_users = requests.get(f"{API_URL}/users/", headers=headers)
            if res_users.status_code == 200:
                for u in res_users.json():
                    if str(u.get('role')).upper() == "COORDINATOR":
                        s_name = site_map.get(u.get('site_id'), "Sede Nacional")
                        table_data.append({
                            "id": u['id'],
                            "full_name": u.get('full_name') or "Sin Asignar",
                            "email": u['email'],
                            "site_name": s_name,
                            "is_active": "Activo" if u['is_active'] else "Inactivo"
                        })
    except Exception as e:
        print("Error loading coordinators:", e)
        
    return table_data, site_options

@callback(
    Output("add-coordinator-modal", "is_open"),
    [Input("btn-open-add-coordinator", "n_clicks"), Input("btn-cancel-add-coordinator", "n_clicks")],
    [State("add-coordinator-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_add_coordinator_modal(n1, n2, is_open):
    return not is_open

@callback(
    Output("add-coordinator-alert", "children"),
    Output("add-coordinator-alert", "color"),
    Output("add-coordinator-alert", "is_open"),
    Input("btn-submit-add-coordinator", "n_clicks"),
    State("add-coord-email", "value"),
    State("add-coord-name", "value"),
    State("add-coord-site-dropdown", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def submit_new_coordinator(n, email, name, site_id, token):
    if not email or not site_id:
        return "El correo y la sede son estrictamente obligatorios.", "warning", True
        
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "email": email,
        "full_name": name,
        "site_id": site_id
    }
    
    try:
        res = requests.post(f"{API_URL}/users/coordinators/quick", json=payload, headers=headers)
        if res.status_code == 200:
            return "Coordinador creado existosamente y vinculado a la sede. Se le ha asignado la contraseña default 'AdminEspora26!'. Cierra el modal para actualizar el panel.", "success", True
        else:
            return f"Error de Servicio: {res.json().get('detail')}", "danger", True
    except Exception as e:
        return f"Corte de Conexión: {e}", "danger", True
