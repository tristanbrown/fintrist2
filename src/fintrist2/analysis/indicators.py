"""Statistical indicators for analysis of price/volume trends."""

def simplemovingavg(df, col, window, centering=False):
    """Simple Moving Average (SMA)"""
    return df[col].rolling(window, center=centering).mean()

def sma_crossover(df, col, fastfreq, slowfreq):
    """SMA Crossover indicator"""
    sma_fast = simplemovingavg(df, col, fastfreq)
    sma_slow = simplemovingavg(df, col, slowfreq)
    return (sma_fast - sma_slow) / sma_slow * 100
