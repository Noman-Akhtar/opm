import ccxt
import random
import numpy as np
import pandas as pd
import datetime as dt
from math import exp, sqrt
from py_vollib.black_scholes_merton.implied_volatility import implied_volatility

from resources import pricing


dbt = ccxt.deribit()


def get_iv(row, side):
    try:
        iv = implied_volatility(
            row['{}_price'.format(side)] * row['index_price'],
            row['index_price'],
            row['strike'],
            row['until_expiry'],
            row['interest_rate'],
            row['q'],
            row['flag']
        )
        iv = round(100 * iv, 2)
    except Exception as e:
        print(e)
        iv = np.nan
    return iv


def get_iv_custom(row, side):
    try:
        if not np.isnan(row['mid_price']):
            iv = pricing.get_implied_vol(
                row['{}_price'.format(side)] * row['index_price'],
                row['index_price'],
                row['strike'],
                row['until_expiry'],
                row['interest_rate'],
                row['flag']
            )
            iv = round(100 * iv, 2)
        else:
            iv = np.nan
    except Exception as e:
        print(e)
        iv = np.nan
    return iv


def get_index(coin):
    index = dbt.public_get_get_index(params={'currency': coin.upper()})['result'][coin.upper()]
    return index


def get_markets(coin, kind):
    markets = pd.DataFrame(
        [each_dict['info'] for each_dict in dbt.fetch_markets()]
    )
    markets = markets[(markets['kind'].isin(kind)) & (markets['base_currency'] == coin.upper())]
    markets['expiration_timestamp'] = pd.to_datetime(markets['expiration_timestamp'], unit='ms')
    markets.sort_values('expiration_timestamp', ascending=True, inplace=True)
    return markets


def get_tickers(coin):
    tickers = pd.DataFrame(
        [value['info'] for _, value in dbt.fetch_tickers(params={'currency': coin.upper()}).items()]
    )
    index = dbt.public_get_get_index(params={'currency': coin.upper()})['result'][coin.upper()]
    tickers['index_price'] = index
    return tickers


def prepare_options(markets, tickers, maturity, interest_rate):

    markets['expiration_timestamp'] = pd.to_datetime(markets['expiration_timestamp'], unit='ms')
    if maturity:
        markets = markets[markets['expiration_timestamp'].dt.strftime('%d-%B-%Y').isin(maturity)]
    option_tickers = tickers[tickers['instrument_name'].isin(markets['instrument_name'])].copy()
    option_tickers['flag'] = option_tickers['instrument_name'].str.split('-').str[-1].str.lower()
    option_tickers['strike'] = option_tickers['instrument_name'].map(
        markets.set_index('instrument_name')['strike']
    )
    option_tickers.sort_values('strike', inplace=True, ascending=True)
    option_tickers['mid_usd'] = option_tickers['mid_price'] * option_tickers['index_price']
    option_tickers['expiration_timestamp'] = option_tickers['instrument_name'].map(
        markets.set_index('instrument_name')['expiration_timestamp']
    )
    option_tickers['until_expiry'] = (option_tickers['expiration_timestamp'] - dt.datetime.now()).dt.total_seconds() / 31556952
    option_tickers['interest_rate'] = interest_rate / 100
    option_tickers['q'] = 0
    option_tickers['iv_mid'] = option_tickers.apply(lambda row: get_iv_custom(row, 'mid'), axis=1)
    option_tickers['iv_bids'] = option_tickers.apply(lambda row: get_iv_custom(row, 'bid'), axis=1)
    option_tickers['iv_asks'] = option_tickers.apply(lambda row: get_iv_custom(row, 'ask'), axis=1)
    option_tickers.rename(
        columns={'index_price': 'index', 'bid_price': 'bid', 'ask_price': 'ask', 'open_interest': 'interest'},
        inplace=True
    )
    return option_tickers


def build_vol_surface(options, side):
    options['expiration'] = options['expiration_timestamp'].dt.strftime('%Y-%m-%d')
    surface = pd.pivot_table(
        options,
        index=['expiration'],
        columns=['strike'],
        values=['iv_{}'.format(side)]
    )
    surface = surface.droplevel(0, axis=1).reset_index()
    surface.sort_values('expiration', ascending=True, inplace=True)
    return surface


def price_options(pricer_table, coin, interest_rate, fit_model):
    index = get_index(coin)
    for each_dict in pricer_table:
        each_dict['index'] = index
        strike = float(each_dict['strike'])
        flag = each_dict['option']
        until_expiry = (pd.to_datetime(each_dict['expiry'], format='%Y-%m-%d %H:%M:%S') - dt.datetime.now()).total_seconds() / 31556952
        v = fit_model([float(strike)])[0] / 100
        each_dict['iv'] = round(v, 2)
        try:
            price = pricing.black_scholes(index, strike, until_expiry, v, interest_rate, flag)
        except:
            price = np.nan
        each_dict['price'] = round(price / index, 4)
    return pricer_table


def get_timestamps(expiration, steps):
    timestamps = np.linspace(
        int(dt.datetime.now().timestamp() * 1000),
        expiration,
        steps
    )
    delta_t = (expiration - int(dt.datetime.now().timestamp() * 1000)) / steps
    return timestamps, delta_t / 31556952


def get_ticker(instrument_name):
    ticker = dbt.public_get_ticker(
        params={'instrument_name': instrument_name}
    )['result']
    return ticker


def get_u_d_p(index, vol, delta_t, interest_rate):
    u = exp(vol * sqrt(delta_t))
    d = exp(-1 * vol * sqrt(delta_t))
    a = exp(interest_rate * delta_t)
    p = (a - d) / (u - d)
    return u, d, p


def price_function(index, interest_rate, vol, t):
    epsilon = round(random.uniform(-1, 1), 2)
    vol_sq = (vol * vol) / 2
    vol_sq = interest_rate - vol_sq
    exp_1 = vol_sq * t
    exp_2 = vol * epsilon * sqrt(t)
    exp_term = exp_1 + exp_2
    exp_term = np.exp(exp_term)
    price = index * exp_term
    return price


def get_monte_carlo_simulations(index, interest_rate, vol, expiration, flag, strike, sims, time_step=60*60*1000):
    steps = (expiration - int(dt.datetime.now().timestamp() * 1000)) / (time_step)
    timeseries = np.linspace(
        int(dt.datetime.now().timestamp() * 1000),
        expiration,
        int(steps)
    )
    timestamps = [i/31556952 for i in timeseries]
    timestamps = pd.Series(timestamps).diff()

    price_series = []
    expected_payoffs = []
    for i in range(sims):
        print(i)
        this_sim_prices = []
        for j in range(len(timestamps)):
            try:
                if j == 0:
                    price = index
                # elif j == 0:
                #     price = price_function(index, interest_rate, vol, timestamps[j])
                else:
                    last_price = this_sim_prices[-1]
                    price = price_function(last_price, interest_rate, vol, timestamps[j])
            except Exception as error:
                break
            this_sim_prices.append(price)

        if flag == 'C':
            payoff = max(this_sim_prices[-1] - strike, 0)
        else:
            payoff = max(this_sim_prices[-1] - strike, 0)
        price_series.append(this_sim_prices)
        if payoff > 0:
            expected_payoffs.append(payoff)

    return timeseries, price_series, expected_payoffs


def get_bs_price(index, strike, expiration, vol, interest_rate, flag):
    expiration = (expiration - int(dt.datetime.now().timestamp() * 1000)) / 31556952
    price = pricing.black_scholes(index, strike, expiration, vol, interest_rate, flag)
    return price
