"""Statistical indicators for analysis of price/volume trends."""
import numpy as np

from . import etl

def simplemovingavg(df, col, window, centering=False):
    """Simple Moving Average (SMA)"""
    col = etl.sanitize_cols(df, col)
    return col.rolling(window, center=centering).mean()

def expmovingavg(df, col, window):
    """Exponential Weighted Moving Average (EMA)"""
    col = etl.sanitize_cols(df, col)
    return col.ewm(span=window).mean()

def sma_crossover(df, col, fastfreq, slowfreq):
    """SMA Crossover indicator"""
    col = etl.sanitize_cols(df, col)
    sma_fast = simplemovingavg(df, col, fastfreq)
    sma_slow = simplemovingavg(df, col, slowfreq)
    return (sma_fast - sma_slow) / sma_slow * 100

def pct_change(df, col1, col2):
    """Give the % change between two columns."""
    col1, col2 = etl.sanitize_cols(df, col1, col2)
    return col2 / col1 - 1

def log_change(df, col1, col2):
    """Give the log change between two columns."""
    col1, col2 = etl.sanitize_cols(df, col1, col2)
    return np.log(col2 / col1)

def rate_of_return(df, col, freq=1, method='log'):
    """Give the log change in a column over time.
    
    freq: number of rows for the time interval
    """
    col = etl.sanitize_cols(df, col)
    if method == 'log':
        rate = log_change
    elif method == 'pct':
        rate = pct_change
    return rate(df, col.shift(freq), col)

def volatility(prices, freq=15, method='close'):
    """Close/Close volatility given by std of natural log returns.
    High/Low volatility is Parkinson volatility.
    https://www.ivolatility.com/help/3.html#:~:text=The%20Parkinson%20number%2C%20or%20High,on%20a%20fixed%20time%20interval.
    ln(xn/xm) ~= (xn - xm)/xm
    https://stats.stackexchange.com/questions/244199/why-is-it-that-natural-log-changes-are-percentage-changes-what-is-about-logs-th
    """
    if method == 'close':
        logreturns = rate_of_return(prices, 'adjClose', 1)
        return logreturns.rolling(freq).std(ddof=0)
    elif method == 'parkinson':
        HLreturns = log_change(prices, 'adjLow', 'adjHigh')
        return HLreturns.rolling(freq).std(ddof=0) / (4 * np.log(2))**(1/2) * 4

def pct_vol_osc(prices, short_freq=21, long_freq=55, sig_freq=13):
    """Percent volume oscillator.

    Plot ppo and sig as lines, diff as a barchart.
    """
    short = expmovingavg(prices, 'adjVolume', short_freq)
    long = expmovingavg(prices, 'adjVolume', long_freq)
    df = prices[['adjVolume']].copy()
    df['vol_ppo'] = (short - long) / long * 100
    df['vol_sig'] = expmovingavg(df, 'vol_ppo', sig_freq)
    df['vol_diff'] = df['vol_ppo'] - df['vol_sig']
    return df
