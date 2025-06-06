import pandas as pd
import matplotlib.pyplot as plt
from indicators import add_indicators

def plot_chart(csv_path):
    df = pd.read_csv(csv_path)
    df = add_indicators(df)
    df = df.dropna()
    plt.figure(figsize=(12,6))
    plt.plot(df['close'], label='Price')
    plt.plot(df['sma5'], label='SMA5')
    plt.plot(df['ema12'], label='EMA12')
    plt.plot(df['ema26'], label='EMA26')
    plt.title('Crypto Price & Indicators')
    plt.legend()
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.show()

if __name__ == "__main__":
    plot_chart("historical_prices.csv")
