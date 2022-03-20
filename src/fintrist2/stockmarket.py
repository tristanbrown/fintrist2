""""""
import time
import pandas as pd
import arrow
import pandas_datareader as pdr
import pandas_market_calendars as mcal

from pandas_datareader.tiingo import TiingoIEXHistoricalReader
from alpaca_management.connect import trade_api
from fintrist2.settings import Config
from fintrist2.models import StockData

class Stock():
    """Pulls stock price data and caches it in MongoDB.

    freq: daily, or Xmin, or Yhour
    """
    
    def __init__(self, symbol, freq='daily', clearcache=False):
        self.symbol = symbol
        self.freq = freq
        self.study = self.get_study()
        self.data = self.get_data(clearcache)

    def __repr__(self):
        return f"Stock: {self.symbol}, {self.freq}"

    def get_study(self):
        """"""
        study = StockData(name=f"{self.symbol}_{self.freq}")
        return study.db_obj

    @property
    def valid(self):
        """Check if the Study data is still valid."""
        # Check the age of the data
        if not self.study.timestamp:
            current = False
        else:
            current = market_current(self.study.timestamp)
        return current

    def get_data(self, clearcache):
        if self.freq == 'daily':
            pull_method = self.pull_daily
            kwargs = {}
        else:
            pull_method = self.pull_intraday
            kwargs = {'freq': self.freq}

        if clearcache or not self.valid:
            start = time.time()
            self.study.data = pull_method(**kwargs)
            self.study.save()
            timelength = time.time() - start
            print(f"Queried data in {timelength:.1f} sec")
        return self.study.data

    def pull_daily(self, source=None, mock=None):
        """Get a stock quote history.

        ::parents:: mock
        ::params:: symbol, source
        ::alerts:: source: AV, source: Tiingo, ex-dividend, split, reverse split
        """
        ## Get the data from whichever source
        if mock is not None:
            source = 'mock'
        elif not source:
            source = 'Tiingo'
        if source == 'AV':
            data = pdr.get_data_alphavantage(self.symbol, api_key=Config.APIKEY_AV, start='1900')
            data.index = pd.to_datetime(data.index)
        elif source == 'Tiingo':
            data = pdr.get_data_tiingo(self.symbol, api_key=Config.APIKEY_TIINGO, start='1900')

            # Multiple stock symbols are possible
            data = data.reset_index().set_index('date')
            data.index = data.index.date
            data.index.name = 'date'
            data = data.set_index('symbol', append=True)
            data = data.reorder_levels(['symbol', 'date'])
            if isinstance(self.symbol, str):  ## Single symbol only
                data = data.droplevel('symbol')
        elif source == 'mock':
            data = mock

        return data

    def pull_intraday(self, day=None, freq='5min', tz=None, source=None, mock=None):
        """Get intraday stock data.

        ::parents:: mock
        ::params:: symbols, day, tz, source
        ::alerts:: source: Alpaca, source: mock
        """
        ## Pick the day
        latest_day = latest_market_day(day)
        open_time = latest_day[0].isoformat()
        close_time = latest_day[1].isoformat()
        if tz is None:
            tz = Config.TZ

        ## Get the data
        if mock is not None:
            dfs = mock
        elif source == 'Alpaca':
            data = trade_api.get_barset(
                self.symbol, timeframe='minute', start=open_time, end=close_time, limit=1000)
            missing = [symbol for symbol, records in data.items() if not records]
            if missing:
                raise ValueError(f"No intraday data found for symbol(s) {', '.join(missing)}.")
            dfs = {symbol: format_stockrecords(records, tz) for symbol, records in data.items()}
        else:
            tiingo = TiingoIEXPriceVolume(self.symbol, api_key=Config.APIKEY_TIINGO, end=day, freq=freq)
            dfs = tiingo.read()

        if isinstance(self.symbol, str):
            dfs = dfs.loc[self.symbol]

        return dfs

class TiingoIEXPriceVolume(TiingoIEXHistoricalReader):
    """Adds volume to the Tiingo/IEX intraday pricing data."""

    @property
    def params(self):
        """Parameters to use in API calls"""
        return {
            "startDate": self.start.strftime("%Y-%m-%d"),
            "endDate": self.end.strftime("%Y-%m-%d"),
            "resampleFreq": self.freq,
            "format": "json",
            "columns": "open,high,low,close,volume",
        }

def format_stockrecords(records, tz):
    """Reformat stock tick records as a dataframe."""
    df = pd.DataFrame.from_records(records.__dict__['_raw'])
    df = df.rename({
        'o': 'open', 'c': 'close',
        'l': 'low', 'h': 'high',
        'v': 'volume', 't': 'timestamp'}, axis=1
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert(tz)
    df = df.set_index('timestamp')
    return df

def market_schedule(start, end, tz=None):
    if tz is None:
        tz = Config.TZ
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start.datetime, end_date=end.datetime)
    try:
        for col in schedule.columns:
            schedule[col] = schedule[col].dt.tz_convert(tz)
    except AttributeError:
        pass
    return schedule, nyse

def market_open(now=None):
    """Is the market open?"""
    nyse = mcal.get_calendar('NYSE')
    if now is None:
        now = arrow.now('America/New_York')
    schedule = nyse.schedule(start_date=now.datetime, end_date=now.datetime)
    return nyse.open_at_time(schedule, now.datetime)  # Market currently open

def latest_market_day(now=None):
    """Get the hours of the most recent time when the market was open."""
    tz = 'America/New_York'
    if now is None:
        now = arrow.now(tz)
    schedule, nyse = market_schedule(now.shift(days=-7), now, tz)
    last_day = schedule.iloc[-1]
    if now.datetime < last_day['market_open']:
        return schedule.iloc[-2]
    else:
        return last_day

def market_current(timestamp):
    """Check if the market has or hasn't progressed since the last timestamp."""
    now = arrow.now(Config.TZ)
    schedule, nyse = market_schedule(timestamp, now)
    is_open = nyse.open_at_time(schedule, now.datetime)  # Market currently open
    open_close_dt = pd.DataFrame([], index=schedule.values.flatten())  ## Market day boundaries
    if is_open:  ## If the market is open, the data should be refreshed
        return False
    elif len(open_close_dt[timestamp.datetime:now.datetime]) > 0: ## A market day boundary has passed
        return False
    else:  ## The market hasn't changed. The data is still valid.
        return True
