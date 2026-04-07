import dash
from dash import html, dcc

dash.register_page(__name__, path='/', name='Home')

layout = html.Div([
    dcc.Location(id='redirect-to-login', pathname='/login', refresh=True)
])
