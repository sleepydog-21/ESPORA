import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import os

app = dash.Dash(
    __name__, 
    use_pages=True, 
    external_stylesheets=[dbc.themes.LUMEN, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Hardcoded for now, read from env in production
API_URL = os.getenv("API_URL", "http://localhost:8000")

app.layout = html.Div([
    dcc.Store(id="auth-token", storage_type="session"),
    dcc.Store(id="user-data", storage_type="session"),
    
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Login", href="/login", id="nav-login")),
            dbc.NavItem(dbc.NavLink("General", href="/general", id="nav-general", style={"display": "none"})),
            dbc.NavItem(dbc.NavLink("Coordinator", href="/coordinator", id="nav-coordinator", style={"display": "none"})),
            dbc.NavItem(dbc.NavLink("Therapist", href="/therapist", id="nav-therapist", style={"display": "none"})),
            dbc.NavItem(dbc.NavLink("Logout", href="/login", id="nav-logout", style={"display": "none"})),
        ],
        brand="ESPORA Platform",
        brand_href="/",
        color="primary",
        dark=True,
    ),
    
    dbc.Container(
        dash.page_container,
        className="mt-4",
        fluid=True
    )
])

if __name__ == '__main__':
    # Run on 8050
    app.run(host='0.0.0.0', port=8050, debug=True)
