NAV_STYLE = {'display': 'inline', 'margin-left': '15px'}
H6_STYLE = {'font-size': '14px', 'font-weight': 'bold'}

COINS = ['BTC', 'ETH']
INTEREST_RATES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
IV_COLUMNS = [
    'strike', 'index', 'bid', 'iv_bids', 'ask', 'iv_asks', 'interest'
]
IV_SIDES = ['mid', 'bids', 'asks']
IV_CPS = ['c', 'p']
LIMITS = [0.1, 0.2, 0.3, 0.4, 0.5]
PRICER_COLUMNS = [
    'expiry', 'strike', 'index', 'option', 'iv', 'interest', 'price'
]
STEPS = [i for i in range(0, 51, 5)]
SIMULATIONS = [i for i in range(100, 5000, 100)]
