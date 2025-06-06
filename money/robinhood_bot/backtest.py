import pandas as pd
from indicators import add_indicators

def backtest(csv_path):
    df = pd.read_csv(csv_path)
    df = add_indicators(df)
    df = df.dropna()
    balance = 1000
    position = 0
    entry_price = 0
    stop_loss = 0.02
    trades = 0

    for i, row in df.iterrows():
        price = row['close']
        # Simple rule: Buy when RSI < 30, Sell when RSI > 70
        if row['rsi14'] < 30 and position == 0:
            position = balance / price
            entry_price = price
            balance = 0
            trades += 1
            print(f"{row['timestamp']}: BUY at {price:.2f}")
        elif row['rsi14'] > 70 and position > 0:
            balance = position * price
            position = 0
            trades += 1
            print(f"{row['timestamp']}: SELL at {price:.2f}")
        elif position > 0 and price < entry_price * (1 - stop_loss):
            balance = position * price
            position = 0
            trades += 1
            print(f"{row['timestamp']}: STOP LOSS SELL at {price:.2f}")

    if position > 0:
        balance = position * df.iloc[-1]['close']
    print(f"Final Balance: ${balance:.2f} | Trades: {trades}")

if __name__ == "__main__":
    backtest("historical_prices.csv")
