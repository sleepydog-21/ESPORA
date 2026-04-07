import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import urllib.parse
from dash import Input, Output, callback

dash.register_page(__name__, path='/kpi_analytics', name='Analítica Nacional de KPI')

layout = dbc.Container([
    dcc.Location(id="kpi-url", refresh=False),
    dbc.Row([
        dbc.Col(html.H2(id="kpi-title", className="my-4 text-primary"), width=12),
    ]),
    dbc.Card([
        dbc.CardBody([
            html.H5("Foco Nacional Inter-Universitario", className="text-muted mb-4"),
            html.P("Esta ventana agrupa las 32 facultades de la UNAM y despliega infografías profundas evaluadas únicamente contra el KPI seleccionado.", className="lead"),
            html.P("Demográficos, varianza estadística y factores socio-económicos cruzados."),
            dbc.Button("Regresar a Control Central", href="/general", color="secondary")
        ])
    ])
], fluid=True)

@callback(
    Output("kpi-title", "children"),
    Input("kpi-url", "search")
)
def update_title(search):
    if search:
        parsed = urllib.parse.parse_qs(search.lstrip('?'))
        kpi = parsed.get("kpi", ["KPI"])[0]
        return f"📊 Análisis Profundo: {kpi}"
    return "Analítica Nacional KPI"
