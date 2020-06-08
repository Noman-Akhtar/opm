import pandas as pd
from math import exp
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

                # COIN
                html.Div(
                    className='two columns',
                    children=[
                        html.H6(children=['Coin'], style=config.H6_STYLE),
                        dcc.RadioItems(
                            id='trees_coin',
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
                            id='trees_interest_rate',
                            min=min(config.INTEREST_RATES),
                            max=max(config.INTEREST_RATES),
                            step=1,
                            marks={i: str(i / 100) for i in config.INTEREST_RATES if i % 2},
                            value=6
                        ),
                    ]
                ),

                # OPTION
                html.Div(
                    className='three columns',
                    children=[
                        html.H6(children=['Option'], style=config.H6_STYLE),
                        dcc.Dropdown(
                            id='trees_option',
                        )
                    ]
                ),

                # VOL
                html.Div(
                    className='one column',
                    children=[
                        html.H6(children=['Vol.'], style=config.H6_STYLE),
                        dcc.Input(
                            id='trees_vol',
                            type='number',
                            style={'width': '100%'}
                        )
                    ]
                ),

                # STEPS
                html.Div(
                    className='one column',
                    children=[
                        html.H6(children=['Steps'], style=config.H6_STYLE),
                        dcc.Dropdown(
                            id='trees_steps',
                            options=[{'label': i, 'value': i} for i in config.STEPS],
                            value=5,
                            style={'width': '100%'}
                        ),
                    ]
                ),

                # BUTTON
                html.Div(
                    className='two columns',
                    children=[
                        html.Button(
                            id='trees_button',
                            children='BUILD TREE',
                            n_clicks=0,
                            style={'margin-top': '35px'}
                        ),
                    ]
                ),

            ]
        ),

        # TREES
        html.Div(
            className='row',
            children=[
                dcc.Graph(
                    id='trees_chart'
                )
            ]
        ),

        # REFRESH
        dcc.Store(id='trees_markets'),
        dcc.Interval(id='trees_refresh', interval=refresh_rate, n_intervals=0)

    ]
)


# --------------------------------
# Callbacks
# --------------------------------
@app.callback(
    [Output('trees_markets', 'data'),
     Output('trees_option', 'options'),
     Output('trees_option', 'value')],
    [Input('trees_coin', 'value')]
)
def get_options(coin):
    markets = functions.get_markets(coin, ['option'])
    instruments = list(markets['instrument_name'].unique())
    options = [{'label': i, 'value': i} for i in instruments]
    value = instruments[0]
    return markets.to_json(orient='split'), options, value


@app.callback(
    Output('trees_chart', 'figure'),
    [Input('trees_button', 'n_clicks'),
     Input('trees_refresh', 'n_intervals')],
    [State('trees_coin', 'value'),
     State('trees_interest_rate', 'value'),
     State('trees_option', 'value'),
     State('trees_vol', 'value'),
     State('trees_steps', 'value'),
     State('trees_markets', 'data')]
)
def build_tree(n_clicks, n_intervals, coin, interest_rate, option, vol, steps, markets):

    if not vol:
        return {}

    interest_rate = interest_rate / 100
    markets = pd.read_json(markets, orient='split')
    ticker = functions.get_ticker(option)
    coin, expiry, strike, flag = option.split('-')
    strike = float(strike)

    expiration = markets[markets['instrument_name'] == option]['expiration_timestamp'].values[0]

    timestamps, delta_t = functions.get_timestamps(expiration, steps)
    index = ticker.get('index_price')
    vol = float(vol/100)
    u, d, p = functions.get_u_d_p(index, vol, delta_t, interest_rate)

    underlying = [(index,)]
    for i in range(0, steps):
        if i == 0:
            continue
        else:
            last_underlying = list(underlying[i-1])
            new_underlying = []
            for each_price in last_underlying:
                up = round(each_price * u, 2)
                down = round(each_price * d, 2)
                new_underlying.extend([up, down])
            new_underlying = list(set(new_underlying))
            new_underlying.sort(reverse=False)
            underlying.append(tuple(new_underlying))

    options_prices = [()] * len(underlying)
    for i in range(1, steps+1):
        i = steps - i
        underlying_price_set = list(underlying[i])
        if i == steps-1:
            option_price_set = []
            for each_price in underlying_price_set:
                option_price = max(each_price - strike, 0) if flag == 'C' else max(strike - each_price, 0)
                option_price = round(option_price, 2)
                option_price_set.append(option_price)
            options_prices[i] = tuple(option_price_set)
        else:
            forward_option_price_set = list(options_prices[i + 1])
            option_price_set = []
            for j in range(len(underlying_price_set)):
                price_a = forward_option_price_set[j]
                price_b = forward_option_price_set[j+1]
                option_price = ((p * price_a) + ((1 - p) * price_b) * exp(-1 * interest_rate * delta_t))
                option_price = round(option_price, 2)
                option_price_set.append(option_price)
            options_prices[i] = tuple(option_price_set)

    chart_data = []
    for i in range(len(underlying)):
        underlying_price_set = list(underlying[i])
        option_price_set = list(options_prices[i])
        x = [pd.to_datetime(timestamps[i], unit='ms')] * len(underlying_price_set)
        chart_data.append(
            go.Scattergl(
                x=x,
                y=underlying_price_set,
                text=['({}), ({})'.format(underlying_price_set[j], option_price_set[j]) for j in range(len(underlying_price_set))],
                textposition="top center",
                mode='markers+text',
            ),
        )

    chart_layout = {
        'margin': {'t': 40, 'b': 40, 'l': 40, 'r': 40},
        'showlegend': False,
        'height': 800
    }
    return {'data': chart_data, 'layout': chart_layout}
