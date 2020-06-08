import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import config
from app import app
from apps import skew, surface, binomial, mc_simulations

app.layout = html.Div(
    children=[

        # NAV
        html.Div(
            className='row',
            style={'margin-bottom': '10px', 'border-bottom': '1px solid lightgray'},
            children=[
                html.Ul(
                    id='nav',
                    style={'margin-top': '15px', 'margin-bottom': '15px'},
                    children=[
                        html.Li(children=[html.A('Skew', href='/skew')], style=config.NAV_STYLE),
                        html.Li(children=[html.A('Surface', href='/surface')], style=config.NAV_STYLE),
                        html.Li(children=[html.A('Binomial Trees', href='/binomial')], style=config.NAV_STYLE),
                        html.Li(children=[html.A('Monte Carlo Sims', href='/mc')], style=config.NAV_STYLE),
                    ],
                ),
            ]
        ),

        dcc.Location(
            id='url',
            refresh=False
        ),
        html.Div(
            id='page-content',
        )
    ]
)


@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/skew':
        return skew.layout
    elif pathname == '/surface':
        return surface.layout
    elif pathname == '/binomial':
        return binomial.layout
    elif pathname == '/mc':
        return mc_simulations.layout
    else:
        return


if __name__ == '__main__':
    app.run_server(debug=False)
