import dash_table
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

        # COLUMN
        html.Div(
            className='three columns',
            children=[

                # COIN
                html.Div(
                    className='row',
                    children=[
                        html.H6(children=['Coin'], style=config.H6_STYLE),
                        dcc.RadioItems(
                            id='iv_coin',
                            options=[{'label': i, 'value': i} for i in config.COINS],
                            value=config.COINS[0],
                            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                        ),
                    ]
                ),

                # INTEREST RATE
                html.Div(
                    className='row',
                    style={'margin-top': '30px'},
                    children=[
                        html.H6(children=['Interest Rate'], style=config.H6_STYLE),
                        dcc.Slider(
                            id='iv_interest_rate',
                            min=min(config.INTEREST_RATES),
                            max=max(config.INTEREST_RATES),
                            step=1,
                            marks={i: str(i / 100) for i in config.INTEREST_RATES if i % 2},
                            value=6
                        ),
                    ]
                ),

                # MATURITY
                html.Div(
                    className='row',
                    style={'margin-top': '30px'},
                    children=[
                        html.H6(children=['Expiration'], style=config.H6_STYLE),
                        dcc.Dropdown(
                            id='iv_expiration',
                        )
                    ]
                ),

                # SKEW BUTTON
                html.Div(
                    className='row',
                    style={'margin-top': '30px'},
                    children=[
                        html.Button(
                            id='iv_skew_button',
                            children='GET SKEW',
                            n_clicks=0
                        ),
                    ]
                ),

            ]
        ),

        # CALLS/PUTS + ChHART
        html.Div(
            className='nine columns',
            children=[

                # CALLS/PUTS
                html.Div(
                    className='row',
                    children=[

                        # PUTS
                        html.Div(
                            className='one-half column',
                            children=[
                                html.H6(children=['Puts'], style=config.H6_STYLE),
                                dash_table.DataTable(
                                    id='iv_puts',
                                    columns=[{'name': i, 'id': i} for i in config.IV_COLUMNS],
                                    page_action='none',
                                    style_table={'height': '400px', 'overflowY': 'auto'}
                                ),
                                dcc.Graph(
                                    id='puts_skew',
                                    config={'displayModeBar': False}
                                )
                            ]
                        ),

                        # CALLS
                        html.Div(
                            className='one-half column',
                            children=[
                                html.H6(children=['Calls'], style=config.H6_STYLE),
                                dash_table.DataTable(
                                    id='iv_calls',
                                    columns=[{'name': i, 'id': i} for i in config.IV_COLUMNS],
                                    page_action='none',
                                    style_table={'height': '400px', 'overflowY': 'auto'}
                                ),
                                dcc.Graph(
                                    id='calls_skew',
                                    config={'displayModeBar': False}
                                )
                            ]
                        ),

                    ]
                ),

            ]
        ),

        # STORAGE
        dcc.Store(id='skew_markets'),
        dcc.Interval(id='iv_refresh', interval=refresh_rate, n_intervals=0)

    ]
)


# --------------------------------
# Callbacks
# --------------------------------
@app.callback(
    [Output('skew_markets', 'data'),
     Output('iv_expiration', 'options'),
     Output('iv_expiration', 'value')],
    [Input('iv_coin', 'value')]
)
def get_maturities(coin):
    markets = functions.get_markets(coin, ['option'])
    expirations = list(markets['expiration_timestamp'].dt.strftime('%d-%B-%Y').unique())
    options = [{'label': i, 'value': i} for i in expirations]
    value = expirations[0]
    return markets.to_json(orient='split'), options, value


@app.callback(
    [Output('iv_calls', 'data'),
     Output('iv_puts', 'data')],
    [Input('iv_refresh', 'n_intervals'),
     Input('iv_skew_button', 'n_clicks')],
    [State('iv_expiration', 'value'),
     State('skew_markets', 'data'),
     State('iv_interest_rate', 'value')]
)
def get_options(n_intervals, n_clicks, expiration, markets, interest_rate):
    if expiration and markets:
        markets = pd.read_json(markets, orient='split')
        coin = markets['base_currency'].unique()[0]
        tickers = functions.get_tickers(coin)
        options = functions.prepare_options(markets, tickers, [expiration], interest_rate)
        calls = options[options['flag'] == 'c']
        puts = options[options['flag'] == 'p']
        return calls.to_dict('rows'), puts.to_dict('rows')
    return [], []


@app.callback(
    Output('puts_skew', 'figure'),
    [Input('iv_puts', 'data')]
)
def get_puts_skew(puts):
    if puts:
        puts = pd.DataFrame(puts)
        puts = puts[puts['interest'] >= 1]
        chart_data = [
            go.Scattergl(
                x=puts['strike'],
                y=puts['iv_bids'],
                name='Bid',
                mode='markers',
            ),
            go.Scattergl(
                x=puts['strike'],
                y=puts['iv_asks'],
                name='Ask',
                mode='markers',
            ),
            go.Bar(
                x=puts['strike'],
                y=puts['interest'],
                name='OI',
                opacity=0.1,
                yaxis='y2'
            ),
        ]
        chart_layout = {
            'xaxis': {'title': 'Strike', 'showline': True},
            'yaxis': {'title': 'IV', 'showline': True},
            'yaxis2': {'title': 'Interest', 'side': 'right', 'showline': True},
            'margin': {'t': 60, 'l': 40, 'r': 40, 'b': 50}
        }
        return {'data': chart_data, 'layout': chart_layout}
    return []


@app.callback(
    Output('calls_skew', 'figure'),
    [Input('iv_calls', 'data')]
)
def get_calls_skew(calls):
    if calls:
        calls = pd.DataFrame(calls)
        calls = calls[calls['interest'] >= 1]
        chart_data = [
            go.Scattergl(
                x=calls['strike'],
                y=calls['iv_bids'],
                name='Bid',
                mode='markers',
            ),
            go.Scattergl(
                x=calls['strike'],
                y=calls['iv_asks'],
                name='Ask',
                mode='markers',
            ),
            go.Bar(
                x=calls['strike'],
                y=calls['interest'],
                name='OI',
                opacity=0.1,
                yaxis='y2'
            ),
        ]
        chart_layout = {
            'xaxis': {'title': 'Strike', 'showline': True},
            'yaxis': {'title': 'IV', 'showline': True},
            'yaxis2': {'title': 'Interest', 'side': 'right', 'showline': True},
            'margin': {'t': 60, 'l': 40, 'r': 40, 'b': 50}
        }
        return {'data': chart_data, 'layout': chart_layout}
    return []
