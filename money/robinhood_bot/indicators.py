import pandas as pd
import talib

def add_indicators(df):
    close = df['close'].values
    df['sma5'] = talib.SMA(close, timeperiod=5)
    df['rsi14'] = talib.RSI(close, timeperiod=14)
    df['ema12'] = talib.EMA(close, timeperiod=12)
    df['ema26'] = talib.EMA(close, timeperiod=26)
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macdsignal'] = macdsignal
    df['macdhist'] = macdhist
    df['volatility'] = pd.Series(close).rolling(window=10).std()
    return df
