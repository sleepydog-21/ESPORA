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
                dbc.CardHeader(html.H4("Identifícate")),
                dbc.CardBody([
                    dbc.Alert("Credenciales incorrectas", id="login-alert", color="danger", is_open=False),
                    dbc.Input(id="login-email", type="email", placeholder="Correo electrónico", className="mb-3"),
                    dbc.Input(id="login-password", type="password", placeholder="Contraseña", className="mb-3"),
                    dbc.Button("Ingresar", id="login-btn", color="primary", className="w-100")
                ])
            ], className="mt-5 shadow-sm")
        ], width=12, md=6, lg=4)
    ], justify="center"),
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
        show = {"display": "block"}
        hide = {"display": "none"}
        return hide, show, show if role in ["admin", "general_coordinator"] else hide, show if role in ["admin", "coordinator"] else hide, show if role in ["admin", "therapist"] else hide
    return {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}
