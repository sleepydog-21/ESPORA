import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import requests
import os

dash.register_page(__name__, path='/login', name='Login')

API_URL = os.getenv("API_URL", "http://localhost:8000")

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div("🌿", style={"fontSize": "2.8rem", "lineHeight": "1", "marginBottom": "0.75rem"}),
                        html.H3("Bienvenido a ESPORA", className="fw-bold mb-1", style={"letterSpacing": "-0.02em"}),
                        html.P("Plataforma de Salud Mental Universitaria", className="text-muted small mb-4"),
                    ], className="text-center pt-3"),
                    
                    dbc.Alert(
                        [html.I(className="bi bi-exclamation-triangle-fill me-2"), "Credenciales incorrectas o cuenta inactiva"],
                        id="login-alert",
                        color="danger",
                        className="py-2 small",
                        is_open=False
                    ),
                    
                    html.Div([
                        dbc.Label("Correo institucional", className="small fw-semibold text-secondary mb-1"),
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="bi bi-envelope")),
                            dbc.Input(id="login-email", type="email", placeholder="tu.nombre@unam.mx", className="py-2")
                        ], className="mb-3"),
                    ]),
                    
                    html.Div([
                        dbc.Label("Contraseña", className="small fw-semibold text-secondary mb-1"),
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="bi bi-lock")),
                            dbc.Input(id="login-password", type="password", placeholder="••••••••", className="py-2")
                        ], className="mb-4"),
                    ]),
                    
                    dbc.Button(
                        [html.I(className="bi bi-box-arrow-in-right me-2"), "Iniciar Sesión"],
                        id="login-btn",
                        color="primary",
                        className="w-100 py-2 fw-semibold shadow-sm"
                    ),
                    
                    html.Div([
                        html.Span("Acceso restringido a personal clínico y coordinadores", className="text-muted", style={"fontSize": "0.75rem"})
                    ], className="text-center mt-4 pb-2")
                ], className="p-4")
            ], className="mt-5 shadow-sm border-0 glass-card")
        ], width=12, md=8, lg=5, xl=4)
    ], justify="center", className="min-vh-75 align-items-center"),
    dcc.Location(id="login-url", refresh=True)
])

@callback(
    Output("auth-token", "data"),
    Output("user-data", "data"),
    Output("login-alert", "is_open"),
    Output("login-url", "href"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True
)
def handle_login(n_clicks, email, password):
    if not email or not password:
        return no_update, no_update, True, no_update
        
    try:
        response = requests.post(f"{API_URL}/token", data={"username": email, "password": password})
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            
            # Fetch user details
            user_response = requests.get(f"{API_URL}/users/me", headers={"Authorization": f"Bearer {token}"})
            user_data = user_response.json() if user_response.status_code == 200 else {}
            
            redirect_url = "/general" if user_data.get("role") == "general_coordinator" else "/coordinator" if user_data.get("role") == "coordinator" else "/therapist" if user_data.get("role") == "therapist" else "/"
            
            return token, user_data, False, redirect_url
        else:
            return no_update, no_update, True, no_update
    except Exception as e:
        print(f"Login error: {e}")
        return no_update, no_update, True, no_update

@callback(
    Output("nav-login", "style"),
    Output("nav-logout", "style"),
    Output("nav-general", "style"),
    Output("nav-coordinator", "style"),
    Output("nav-therapist", "style"),
    Input("user-data", "data")
)
def update_navbar(user_data):
    if user_data:
        role = user_data.get("role")
        if role == "general_coordinator":
            return {"display": "none"}, {"display": "block"}, {"display": "block"}, {"display": "none"}, {"display": "none"}
        
        if role == "coordinator":
            return {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "block"}, {"display": "none"}
            
        if role == "therapist":
            return {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "block"}
            
    return {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}
