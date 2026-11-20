import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import os

app = dash.Dash(
    __name__, 
    use_pages=True,
    title="ESPORA Psicológica — Plataforma Clínica",
    external_stylesheets=[dbc.themes.LUMEN, dbc.icons.BOOTSTRAP],
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js"
    ],
    suppress_callback_exceptions=True
)

# Hardcoded for now, read from env in production
API_URL = os.getenv("API_URL", "http://localhost:8000")

app.layout = html.Div([
    dcc.Store(id="auth-token", storage_type="session"),
    dcc.Store(id="user-data", storage_type="session"),
    
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand(
                html.Div([
                    html.Img(
                        src="/assets/espora_logo.png",
                        alt="ESPORA Psicológica",
                        style={"height": "38px", "width": "auto", "objectFit": "contain"}
                    ),
                    html.Span("Plataforma Clínica", className="navbar-brand-badge ms-2 d-none d-sm-inline-block")
                ], className="navbar-brand-espora"),
                href="/",
                className="d-flex align-items-center py-0"
            ),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-box-arrow-in-right me-1"), "Ingresar"], href="/login", id="nav-login", className="nav-link-espora")),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-pie-chart-fill me-1"), "General"], href="/general", id="nav-general", className="nav-link-espora", style={"display": "none"})),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-person-lines-fill me-1"), "Coordinación"], href="/coordinator", id="nav-coordinator", className="nav-link-espora", style={"display": "none"})),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-heart-pulse-fill me-1"), "Consultorio"], href="/therapist", id="nav-therapist", className="nav-link-espora", style={"display": "none"})),
                dbc.NavItem(dbc.Button([html.I(className="bi bi-key-fill me-1"), "Cambiar Contraseña"], id="nav-change-pwd", color="outline-secondary", size="sm", className="ms-2 nav-pwd-btn", style={"display": "none"})),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-box-arrow-right me-1"), "Salir"], href="/login", id="nav-logout", className="nav-link-espora nav-link-logout", style={"display": "none"})),
            ], className="ms-auto d-flex align-items-center gap-1", navbar=True)
        ], fluid=True, className="px-4"),
        className="navbar-espora shadow-sm",
        dark=False,
        color="white"
    ),
    
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("🔑 Cambiar Mi Contraseña")),
        dbc.ModalBody([
            html.P("Ingresa tu contraseña actual (o la llave genérica temporal que te fue asignada) y define tu nueva contraseña personal.", className="text-muted small mb-3"),
            dbc.Alert(id="change-pwd-alert", is_open=False, duration=5000, className="py-2 small"),
            dbc.Label("Contraseña Actual / Llave Genérica:", className="small fw-semibold"),
            dbc.Input(id="change-pwd-current", type="password", placeholder="Ej. Espora2026! o AdminEspora26!", className="mb-3"),
            dbc.Label("Nueva Contraseña (mínimo 6 caracteres):", className="small fw-semibold"),
            dbc.Input(id="change-pwd-new", type="password", placeholder="••••••••", className="mb-3"),
            dbc.Label("Confirmar Nueva Contraseña:", className="small fw-semibold"),
            dbc.Input(id="change-pwd-confirm", type="password", placeholder="••••••••", className="mb-2"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="btn-cancel-change-pwd", color="secondary", outline=True),
            dbc.Button("Guardar Nueva Contraseña", id="btn-submit-change-pwd", color="primary", className="fw-semibold")
        ])
    ], id="change-password-modal", is_open=False),
    
    dbc.Container(
        dash.page_container,
        className="py-4 px-4",
        fluid=True
    )
])

if __name__ == '__main__':
    # Run on 8050
    app.run(host='0.0.0.0', port=8050, debug=True)
