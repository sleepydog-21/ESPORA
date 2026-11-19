import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import os

app = dash.Dash(
    __name__, 
    use_pages=True, 
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
                html.Span([
                    "🌿 ESPORA",
                    html.Span("Salud Mental", className="navbar-brand-badge ms-2")
                ], className="navbar-brand-espora"),
                href="/",
                className="d-flex align-items-center"
            ),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-box-arrow-in-right me-1"), "Ingresar"], href="/login", id="nav-login", className="nav-link-espora")),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-pie-chart-fill me-1"), "General"], href="/general", id="nav-general", className="nav-link-espora", style={"display": "none"})),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-person-lines-fill me-1"), "Coordinación"], href="/coordinator", id="nav-coordinator", className="nav-link-espora", style={"display": "none"})),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-heart-pulse-fill me-1"), "Consultorio"], href="/therapist", id="nav-therapist", className="nav-link-espora", style={"display": "none"})),
                dbc.NavItem(dbc.NavLink([html.I(className="bi bi-box-arrow-right me-1"), "Salir"], href="/login", id="nav-logout", className="nav-link-espora text-danger", style={"display": "none"})),
            ], className="ms-auto d-flex align-items-center gap-1", navbar=True)
        ], fluid=True, className="px-4"),
        className="navbar-espora shadow-sm",
        dark=True
    ),
    
    dbc.Container(
        dash.page_container,
        className="py-4 px-4",
        fluid=True
    )
])

if __name__ == '__main__':
    # Run on 8050
    app.run(host='0.0.0.0', port=8050, debug=True)
