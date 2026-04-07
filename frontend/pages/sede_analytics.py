import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import urllib.parse
from dash import Input, Output, callback

dash.register_page(__name__, path='/sede_analytics', name='Analítica de Sede')

layout = dbc.Container([
    dcc.Location(id="sede-url", refresh=False),
    dbc.Row([
        dbc.Col(html.H2(id="sede-title", className="my-4 text-primary"), width=12),
    ]),
    dbc.Card([
        dbc.CardBody([
            html.H5("Análisis Desplegado", className="text-muted mb-4"),
            html.P("Esta ventana cargaría automáticamente todos los componentes de la vista del Coordinador (Tabla de Espera, Expedientes Activos y Deserciones) pre-filtrados orgánicamente para la Facultad seleccionada.", className="lead"),
            html.P("Al proveer la URL el engine de autenticación se encarga de servir los datos restrictivos."),
            dbc.Button("Regresar a Control Central", href="/general", color="primary")
        ])
    ])
], fluid=True)

@callback(
    Output("sede-title", "children"),
    Input("sede-url", "search")
)
def update_title(search):
    if search:
        parsed = urllib.parse.parse_qs(search.lstrip('?'))
        sede = parsed.get("sede", ["Sede"])[0]
        return f"🏦 Expedientes y Analítica: {sede}"
    return "Analítica de Sede"
