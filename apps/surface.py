import dash_table
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import config
from app import app
from resources import functions


# --------------------------------
# PAGE ENVIRONMENT
# --------------------------------
refresh_rate = 10 * 1000


# --------------------------------
# Layout
# --------------------------------
layout = html.Div(
    className='row',
    children=[

        # PANNEL
        html.Div(
            className='row',
            children=[
                # Coin
                html.Div(
                    className='two columns',
                    children=[
                        html.H6(children=['Coin'], style=config.H6_STYLE),
                        dcc.RadioItems(
                            id='surface_coin',
                            options=[{'label': i, 'value': i} for i in config.COINS],
                            value=config.COINS[0],
                            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                        )
                    ]
                ),
                # INTEREST RATE
                html.Div(
                    className='three columns',
                    children=[
                        html.H6(children=['Interest Rate'], style=config.H6_STYLE),
                        dcc.Slider(
                            id='surface_interest_rate',
                            min=min(config.INTEREST_RATES),
                            max=max(config.INTEREST_RATES),
                            step=1,
                            marks={i: str(i / 100) for i in config.INTEREST_RATES if i % 2},
                            value=6
                        ),
                    ]
                ),
                # IV SIDE
                html.Div(
                    className='two columns',
                    children=[
                        html.H6(children=['IV Side'], style=config.H6_STYLE),
                        dcc.RadioItems(
                            id='surface_side',
                            options=[{'label': i, 'value': i} for i in config.IV_SIDES],
                            value=config.IV_SIDES[0],
                            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                        ),
                    ]
                ),
                # LIMITS
                html.Div(
                    className='three columns',
                    children=[
                        html.H6(children=['Strike Range'], style=config.H6_STYLE),
                        dcc.RadioItems(
                            id='surface_limits',
                            options=[{'label': i, 'value': i} for i in config.LIMITS],
                            value=0.2,
                            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                        )
                    ]
                ),
                # BUTTON
                html.Div(
                    className='two columns',
                    children=[
                        dcc.RadioItems(
                            id='surface_cp',
                            options=[{'label': i, 'value': i} for i in config.IV_CPS],
                            value=config.IV_CPS[0],
                            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                        ),
                        html.Button(
                            id='surface_button',
                            children='GET SURFACE',
                            n_clicks=0,
                            style={'margin-top': '15px'}
                        ),
                    ]
                ),
            ]
        ),

        # Surface
        html.Div(
            className='row',
            children=[
                html.H6(children=['Vol Surface'], style=config.H6_STYLE),
                dash_table.DataTable(id='vol_surface')
            ]
        ),

        # PLOTS + PRICER
        html.Div(
            className='row',
            style={'margin-top': '30px'},
            children=[
                html.H6(children=['Pricing'], style=config.H6_STYLE),
            ]
        ),

        html.Div(
            className='row',
            children=[

                # Pricer Table
                html.Div(
                    className='six columns',
                    children=[

                        html.Div(
                            className='row',
                            children=[
                                dash_table.DataTable(
                                    id='pricer_table',
                                    columns=[
                                        {'name': i, 'id': i} if i not in ['option'] else {'name': i, 'id': i,
                                                                                          'presentation': 'dropdown'}
                                        for i in config.PRICER_COLUMNS
                                    ],
                                    editable=True,
                                    dropdown={
                                        'option': {
                                            'options': [{'label': i, 'value': i} for i in config.IV_CPS]
                                        }
                                    }
                                ),
                            ]
                        ),

                        html.Div(
                            className='row',
                            style={'margin-top': '20px'},
                            children=[
                                html.Div(
                                    className='three columns',
                                    children=[
                                        html.Button(
                                            id='add_option_button',
                                            children=['Add Option'],
                                            n_clicks=0
                                        ),
                                        html.Div(id='add_option_clicks', children=0, style={'display': 'none'}),
                                    ]
                                ),
                                html.Div(
                                    className='three columns',
                                    children=[
                                        html.Button(
                                            id='pricer_button',
                                            children=['Price Option'],
                                            n_clicks=0
                                        ),
                                        html.Div(id='pricer_clicks', children=0, style={'display': 'none'}),
                                    ]
                                )
                            ]
                        ),

                    ]
                ),

                # Pricer Table
                html.Div(
                    className='six columns',
                    children=[

                        html.Div(
                            className='row',
                            children=[
                                dcc.Graph(id='iv_vs_strike')
                            ]
                        ),
                        html.Div(
                            className='row',
                            children=[
                                dcc.Graph(id='iv_vs_expiry')
                            ]
                        ),

                    ]
                ),

            ]
        ),

        # STORAGE
        dcc.Store(id='surface_markets'),
        dcc.Interval(id='surface_refresh', interval=refresh_rate, n_intervals=0)

    ]
)


# --------------------------------
# Callbacks
# --------------------------------
@app.callback(
    Output('surface_markets', 'data'),
    [Input('surface_coin', 'value')]
)
def get_markets(coin):
    markets = functions.get_markets(coin, ['option'])
    return markets.to_json(orient='split')


@app.callback(
    [Output('vol_surface', 'columns'),
     Output('vol_surface', 'data')],
    [Input('surface_button', 'n_clicks')],
    [State('surface_markets', 'data'),
     State('surface_interest_rate', 'value'),
     State('surface_side', 'value'),
     State('surface_cp', 'value'),
     State('surface_limits', 'value')]
)
def get_surface(n_clicks, markets, interest_rate, side, cp, limit):
    if not markets:
        return [], []
    interest_rate = interest_rate / 100
    markets = pd.read_json(markets, orient='split')
    coin = markets['base_currency'].unique()[0]
    tickers = functions.get_tickers(coin)
    options = functions.prepare_options(markets, tickers, [], interest_rate)
    options = options[options['flag'] == cp]
    surface = functions.build_vol_surface(options, side)
    index = options['index'].unique()[0]
    columns = [strike for strike in list(options['strike'].unique()) if (1 - limit) * index <= strike <= (1 + limit) * index]
    columns = [{'name': i, 'id': i} for i in ['expiration'] + columns if i in surface.columns]
    return columns, surface.to_dict('rows')


@app.callback(
    [Output('iv_vs_strike', 'figure'),
     Output('iv_vs_expiry', 'figure')],
    [Input('vol_surface', 'active_cell')],
    [State('vol_surface', 'data')]
)
def make_charts(active_cell, data):

    if active_cell and data:

        # Expiry and Strike
        expiry = data[active_cell['row']]['expiration']
        strike = active_cell['column_id']

        # IV Dataframes
        iv_vs_strike = pd.DataFrame([
            {'strike': key, 'iv': value} for key, value in data[active_cell['row']].items() if key != 'expiration'
        ])
        iv_vs_expiry = pd.DataFrame([
            {'expiry': each_dict['expiration'], 'iv': each_dict[str(strike)]} for each_dict in data
        ])
        iv_vs_strike = iv_vs_strike[~iv_vs_strike['iv'].isna()]
        iv_vs_expiry = iv_vs_expiry[~iv_vs_expiry['iv'].isna()]

        # Fit model (IV STRIKE)
        coef_iv_vs_strike = np.polyfit(
            np.array(pd.to_numeric(iv_vs_strike['strike'])),
            np.array(pd.to_numeric(iv_vs_strike['iv'])),
            3
        )
        spl_iv_vs_strike = np.poly1d(coef_iv_vs_strike)
        xx_iv_vs_strike = np.linspace(
            pd.to_numeric(iv_vs_strike['strike']).min(),
            pd.to_numeric(iv_vs_strike['strike']).max()
        )
        yy_iv_vs_strike = spl_iv_vs_strike(xx_iv_vs_strike)

        # First Chart
        data_iv_vs_strike = [
            go.Scattergl(
                x=iv_vs_strike['strike'],
                y=iv_vs_strike['iv'],
                name='IV',
                mode='markers',
            ),
            go.Scattergl(
                x=xx_iv_vs_strike,
                y=yy_iv_vs_strike,
                name='Fit',
                mode='lines',
            ),
        ]
        layout_iv_vs_strike = {
            'xaxis': {'title': 'Strike', 'showline': True},
            'yaxis': {'title': 'IV', 'showline': True},
            'margin': {'t': 10, 'l': 40, 'r': 40, 'b': 50},
            'height': 300
        }
        iv_vs_strike = {'data': data_iv_vs_strike, 'layout': layout_iv_vs_strike}

        # Second Chart
        data_iv_vs_expiry = [
            go.Scattergl(
                x=iv_vs_expiry['expiry'],
                y=iv_vs_expiry['iv'],
                name='IV',
                mode='markers',
            ),
        ]
        layout_iv_vs_expiry = {
            'xaxis': {'title': 'Expiry', 'showline': True},
            'yaxis': {'title': 'IV', 'showline': True},
            'margin': {'t': 10, 'l': 40, 'r': 40, 'b': 50},
            'height': 300
        }
        iv_vs_expiry = {'data': data_iv_vs_expiry, 'layout': layout_iv_vs_expiry}

        return iv_vs_strike, iv_vs_expiry

    return {}, {}


@app.callback(
    [Output('pricer_table', 'data'),
     Output('add_option_clicks', 'children'),
     Output('pricer_clicks', 'children')],
    [Input('vol_surface', 'active_cell'),
     Input('add_option_button', 'n_clicks'),
     Input('pricer_button', 'n_clicks')],
    [State('surface_coin', 'value'),
     State('surface_interest_rate', 'value'),
     State('vol_surface', 'data'),
     State('pricer_table', 'data'),
     State('add_option_clicks', 'children'),
     State('pricer_clicks', 'children')]
)
def fill_pricing_table(active_cell, add_option, price_option, coin, interest_rate, vol_surface, pricer_table, add_option_clicks, pricer_clicks):
    add_option_clicks = int(add_option_clicks)
    pricer_clicks = int(pricer_clicks)
    interest_rate = interest_rate / 100

    if not active_cell and not vol_surface:
        return pricer_table, add_option_clicks, pricer_clicks

    # Expiry and Strike
    expiry = vol_surface[active_cell['row']]['expiration']
    pricer_table = [] if not pricer_table else pricer_table

    if add_option_clicks != add_option:

        pricer_table = pricer_table + [{
            'expiry': expiry + ' 08:00:00',
            'interest': interest_rate
        }]
        add_option_clicks = add_option

        return pricer_table, add_option_clicks, pricer_clicks

    if pricer_clicks != price_option:

        # IV Dataframes
        iv_vs_strike = pd.DataFrame([
            {'strike': key, 'iv': value} for key, value in vol_surface[active_cell['row']].items() if key != 'expiration'
        ])
        iv_vs_strike = iv_vs_strike[~iv_vs_strike['iv'].isna()]
        iv_vs_strike['strike'] = pd.to_numeric(iv_vs_strike['strike'])
        iv_vs_strike['iv'] = pd.to_numeric(iv_vs_strike['iv'])

        # Fit model
        coeffs = np.polyfit(
            np.array(iv_vs_strike['strike']),
            np.array(iv_vs_strike['iv']),
            3
        )
        fit_model = np.poly1d(coeffs)
        xx = np.linspace(
            iv_vs_strike['strike'].min(),
            iv_vs_strike['strike'].max()
        )
        yy = fit_model(xx)

        # PRICE
        pricer_table = functions.price_options(pricer_table, coin, interest_rate, fit_model)
        pricer_clicks = price_option

        return pricer_table, add_option_clicks, pricer_clicks

    return pricer_table, add_option_clicks, pricer_clicks