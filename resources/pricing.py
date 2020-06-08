from scipy.stats import norm
from math import log, sqrt, exp


def get_ds(s, k, t, v, r):
    d1 = (log(s/k) + t * (r + ((v * v) / 2))) / (v * sqrt(t))
    d2 = d1 - (v * sqrt(t))
    return d1, d2


def vega(s, k, t, v, r):
    d1, d2 = get_ds(s, k, t, v, r)
    option_vega = s * norm.pdf(d1) * sqrt(t)
    return option_vega


def black_scholes(s, k, t, v, r, flag):
    d1, d2 = get_ds(s, k, t, v, r)
    if flag == 'c':
        px = s * norm.cdf(d1) - k * norm.cdf(d2) * exp(-1 * r * t)
    else:
        px = k * norm.cdf(-1 * d2) * exp(-1 * r * t) - s * norm.cdf(-1 * d1)
    return px


def get_implied_vol(m_px, s, k, t, r, flag, tolerance=0.001, epsilon=1, max_iterations=1000):
    v = 0.5
    count = 0
    while epsilon > tolerance:
        count += 1
        if count >= max_iterations:
            print('Max iterations reached. Exiting...')
            return None
        prev_v = v
        diff = black_scholes(s, k, t, v, r, flag) - m_px
        option_vega = vega(s, k, t, v, r)
        v = -diff / option_vega + v
        epsilon = abs((v - prev_v) / prev_v)
    return v

