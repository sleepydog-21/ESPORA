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
                        dbc.Button(
                            [html.I(className="bi bi-envelope-check me-1"), "¿Olvidaste tu contraseña? Recupérala por correo"],
                            id="btn-open-forgot-pwd",
                            color="link",
                            size="sm",
                            className="text-decoration-none fw-semibold mt-3"
                        )
                    ], className="text-center"),
                    
                    html.Div([
                        html.Span("Acceso restringido a personal clínico y coordinadores", className="text-muted", style={"fontSize": "0.75rem"})
                    ], className="text-center mt-2 pb-2")
                ], className="p-4")
            ], className="mt-5 shadow-sm border-0 glass-card")
        ], width=12, md=8, lg=5, xl=4)
    ], justify="center", className="min-vh-75 align-items-center"),

    # Modal de Recuperación de Contraseña por Correo
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("🔐 Recuperar Contraseña por Correo")),
        dbc.ModalBody([
            dbc.Alert(id="forgot-pwd-alert", is_open=False, duration=8000, className="py-2 small"),
            html.P("1. Ingresa tu correo institucional para recibir un código de verificación de 6 dígitos:", className="small text-muted mb-2"),
            dbc.InputGroup([
                dbc.Input(id="forgot-pwd-email", type="email", placeholder="tu.correo@unam.mx"),
                dbc.Button([html.I(className="bi bi-send me-1"), "Enviar Código"], id="btn-send-recovery-code", color="info", className="fw-semibold")
            ], className="mb-3"),
            html.Hr(),
            html.P("2. Ingresa el código de 6 dígitos recibido en tu correo y define tu nueva contraseña:", className="small text-muted mb-2"),
            dbc.Label("Código de 6 dígitos:", className="small fw-semibold"),
            dbc.Input(id="forgot-pwd-code", type="text", placeholder="Ej. 482910", maxLength=6, className="mb-2"),
            dbc.Label("Nueva Contraseña (mínimo 6 caracteres):", className="small fw-semibold"),
            dbc.Input(id="forgot-pwd-new", type="password", placeholder="••••••••", className="mb-2"),
            dbc.Label("Confirmar Nueva Contraseña:", className="small fw-semibold"),
            dbc.Input(id="forgot-pwd-confirm", type="password", placeholder="••••••••", className="mb-2"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cerrar", id="btn-close-forgot-pwd", color="secondary", outline=True),
            dbc.Button("Restablecer Contraseña", id="btn-submit-reset-pwd", color="primary", className="fw-semibold")
        ])
    ], id="forgot-pwd-modal", is_open=False),

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
    Output("nav-change-pwd", "style"),
    Input("user-data", "data")
)
def update_navbar(user_data):
    if user_data:
        role = user_data.get("role")
        if role in ["general_coordinator", "admin"]:
            return {"display": "none"}, {"display": "block"}, {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "inline-block"}
        
        if role == "coordinator":
            return {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "inline-block"}
            
        if role in ["therapist", "api_therapist"]:
            return {"display": "none"}, {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "block"}, {"display": "inline-block"}
            
    return {"display": "block"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}


@callback(
    Output("change-password-modal", "is_open"),
    Input("nav-change-pwd", "n_clicks"),
    Input("btn-cancel-change-pwd", "n_clicks"),
    State("change-password-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_change_password_modal(n_open, n_cancel, is_open):
    if n_open or n_cancel:
        return not is_open
    return is_open


@callback(
    Output("change-pwd-alert", "children"),
    Output("change-pwd-alert", "color"),
    Output("change-pwd-alert", "is_open"),
    Output("change-pwd-current", "value"),
    Output("change-pwd-new", "value"),
    Output("change-pwd-confirm", "value"),
    Input("btn-submit-change-pwd", "n_clicks"),
    State("change-pwd-current", "value"),
    State("change-pwd-new", "value"),
    State("change-pwd-confirm", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True
)
def submit_change_password(n_clicks, current_pwd, new_pwd, confirm_pwd, token):
    if not n_clicks or not token:
        return no_update, no_update, False, no_update, no_update, no_update
    if not current_pwd or not new_pwd or not confirm_pwd:
        return "Todos los campos son obligatorios.", "warning", True, no_update, no_update, no_update
    if new_pwd != confirm_pwd:
        return "La nueva contraseña y su confirmación no coinciden.", "danger", True, no_update, no_update, no_update
    if len(new_pwd.strip()) < 6:
        return "La nueva contraseña debe tener al menos 6 caracteres.", "warning", True, no_update, no_update, no_update

    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(
            f"{API_URL}/users/me/change-password",
            json={"current_password": current_pwd, "new_password": new_pwd.strip()},
            headers=headers
        )
        if res.status_code == 200:
            return "✅ ¡Contraseña actualizada con éxito! La próxima vez que inicies sesión usa tu nueva contraseña.", "success", True, "", "", ""
        detail = res.json().get("detail", res.text)
        return f"Error: {detail}", "danger", True, no_update, no_update, no_update
    except Exception as e:
        return f"Error de conexión: {str(e)}", "danger", True, no_update, no_update, no_update


@callback(
    Output("forgot-pwd-modal", "is_open"),
    Input("btn-open-forgot-pwd", "n_clicks"),
    Input("btn-close-forgot-pwd", "n_clicks"),
    State("forgot-pwd-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_forgot_pwd_modal(n_open, n_close, is_open):
    if n_open or n_close:
        return not is_open
    return is_open


@callback(
    Output("forgot-pwd-alert", "children"),
    Output("forgot-pwd-alert", "color"),
    Output("forgot-pwd-alert", "is_open"),
    Output("forgot-pwd-code", "value"),
    Output("forgot-pwd-new", "value"),
    Output("forgot-pwd-confirm", "value"),
    Input("btn-send-recovery-code", "n_clicks"),
    Input("btn-submit-reset-pwd", "n_clicks"),
    State("forgot-pwd-email", "value"),
    State("forgot-pwd-code", "value"),
    State("forgot-pwd-new", "value"),
    State("forgot-pwd-confirm", "value"),
    prevent_initial_call=True
)
def handle_forgot_and_reset_password(n_send, n_reset, email, code, new_pwd, confirm_pwd):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, False, no_update, no_update, no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if not email or not email.strip():
        return "Por favor ingresa tu correo institucional.", "warning", True, no_update, no_update, no_update

    if trigger_id == "btn-send-recovery-code":
        try:
            res = requests.post(f"{API_URL}/users/forgot-password", json={"email": email.strip()})
            if res.status_code == 200:
                msg = res.json().get("message", "Código enviado a tu correo.")
                return f"📨 {msg} Revisa tu bandeja de entrada e ingrésalo abajo.", "info", True, no_update, no_update, no_update
            detail = res.json().get("detail", res.text)
            return f"Error: {detail}", "danger", True, no_update, no_update, no_update
        except Exception as e:
            return f"Error de conexión: {str(e)}", "danger", True, no_update, no_update, no_update

    if trigger_id == "btn-submit-reset-pwd":
        if not code or not new_pwd or not confirm_pwd:
            return "Ingresa el código de 6 dígitos y confirma tu nueva contraseña.", "warning", True, no_update, no_update, no_update
        if new_pwd != confirm_pwd:
            return "La nueva contraseña y su confirmación no coinciden.", "danger", True, no_update, no_update, no_update
        if len(new_pwd.strip()) < 6:
            return "La nueva contraseña debe tener al menos 6 caracteres.", "warning", True, no_update, no_update, no_update
        try:
            res = requests.post(
                f"{API_URL}/users/reset-password",
                json={"email": email.strip(), "code": code.strip(), "new_password": new_pwd.strip()}
            )
            if res.status_code == 200:
                msg = res.json().get("message", "Contraseña restablecida.")
                return f"✅ {msg}", "success", True, "", "", ""
            detail = res.json().get("detail", res.text)
            return f"Error: {detail}", "danger", True, no_update, no_update, no_update
        except Exception as e:
            return f"Error de conexión: {str(e)}", "danger", True, no_update, no_update, no_update

    return no_update, no_update, False, no_update, no_update, no_update
