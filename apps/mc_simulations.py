import dash_table
import numpy as np
import pandas as pd
from math import sqrt
import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import config
from app import app
from resources import functions


# --------------------------------
# Layout
# --------------------------------
layout = html.Div(
    className='row',
    children=[

        # Panel
        html.Div(
            className='row',
            children=[

                # COIN
                html.Div(
                    className='two columns',
                    children=[
                        html.H6(children=['Coin'], style=config.H6_STYLE),
                        dcc.RadioItems(
                            id='mc_coin',
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
                            id='mc_interest_rate',
                            min=min(config.INTEREST_RATES),
                            max=max(config.INTEREST_RATES),
                            step=1,
                            marks={i: str(i / 100) for i in config.INTEREST_RATES if i % 2},
                            value=1
                        ),
                    ]
                ),

                # OPTION
                html.Div(
                    className='three columns',
                    children=[
                        html.H6(children=['Option'], style=config.H6_STYLE),
                        dcc.Dropdown(
                            id='mc_option',
                        )
                    ]
                ),

                # VOL
                html.Div(
                    className='one column',
                    children=[
                        html.H6(children=['Vol.'], style=config.H6_STYLE),
                        dcc.Input(
                            id='mc_vol',
                            type='number',
                            style={'width': '100%'}
                        )
                    ]
                ),

                # STEPS
                html.Div(
                    className='one column',
                    children=[
                        html.H6(children=['Sims.'], style=config.H6_STYLE),
                        dcc.Dropdown(
                            id='mc_steps',
                            options=[{'label': i, 'value': i} for i in config.SIMULATIONS],
                            value=100,
                            style={'width': '100%'}
                        ),
                    ]
                ),

                # BUTTON
                html.Div(
                    className='two columns',
                    children=[
                        html.Button(
                            id='mc_button',
                            children='RUN SIMULS.',
                            n_clicks=0,
                            style={'margin-top': '35px'}
                        ),
                    ]
                ),

            ]
        ),

        html.Div(
            className='row',
            children=[
                dcc.Graph(id='mc_chart')
            ]
        ),

        html.Div(
            className='row',
            style={'margin-top': '20px'},
            children=[
                html.Div(
                    className='six columns',
                    children=[
                        html.H6(children=['Expected Payoff (dollar amount)'], style=config.H6_STYLE),
                        dash_table.DataTable(
                            id='mc_payoff',
                            columns=[{'name': i, 'id': i} for i in ['mean_payoff', 'std', 'std_error', 'range', 'B.S. price']]
                        )
                    ]
                ),
            ]
        ),

        # STORE
        dcc.Store(id='mc_markets'),

    ]
)


# --------------------------------
# Callbacks
# --------------------------------
@app.callback(
    [Output('mc_markets', 'data'),
     Output('mc_option', 'options'),
     Output('mc_option', 'value')],
    [Input('mc_coin', 'value')]
)
def get_options(coin):
    markets = functions.get_markets(coin, ['option'])
    instruments = list(markets['instrument_name'].unique())
    options = [{'label': i, 'value': i} for i in instruments]
    value = instruments[0]
    return markets.to_json(orient='split'), options, value


@app.callback(
    [Output('mc_chart', 'figure'),
     Output('mc_payoff', 'data')],
    [Input('mc_button', 'n_clicks')],
    [State('mc_coin', 'value'),
     State('mc_interest_rate', 'value'),
     State('mc_option', 'value'),
     State('mc_vol', 'value'),
     State('mc_steps', 'value'),
     State('mc_markets', 'data')]
)
def run_simulations(n_clicks, coin, interest_rate, option, vol, sims, markets):

    if not vol:
        return {}, []

    markets = pd.read_json(markets, orient='split')
    coin, expiry, strike, flag = option.split('-')
    expiration = markets[markets['instrument_name'] == option]['expiration_timestamp'].values[0]

    ticker = functions.get_ticker(option)
    index = ticker.get('index_price')
    vol = float(vol/100)
    interest_rate = interest_rate / 100
    strike = float(strike)

    timestamps, price_series, payoffs = functions.get_monte_carlo_simulations(
        index, interest_rate, vol, expiration, flag, strike, sims, 60*60
    )

    timestamps = [pd.to_datetime(i, unit='ms') for i in timestamps]

    chart_data = []
    for i in range(len(price_series)):
        chart_data.append(
            go.Scattergl(
                x=timestamps,
                y=price_series[i],
                mode='lines',
            ),
        )

    chart_layout = {
        'margin': {'t': 40, 'b': 40, 'l': 40, 'r': 40},
        'showlegend': False,
    }

    payoff_df = {
        'mean_payoff': round(np.mean(payoffs), 2),
        'std': round(np.std(payoffs), 2),
        'std_error': round(np.std(payoffs) / sqrt(sims), 2),
        'range': '{} - {}'.format(
            round(np.mean(payoffs) - (1.96 * (np.std(payoffs) / sqrt(sims))), 2),
            round(np.mean(payoffs) + (1.96 * (np.std(payoffs) / sqrt(sims))), 2)
        ),
        'B.S. price': round(functions.get_bs_price(index, strike, expiration, vol, interest_rate, flag), 2)
    }
    payoff_df = pd.DataFrame([payoff_df])

    return {'data': chart_data, 'layout': chart_layout}, payoff_df.to_dict('rows')
