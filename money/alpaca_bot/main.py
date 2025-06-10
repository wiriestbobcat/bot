import os
import openai
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
from datetime import datetime, timezone
import time
import requests
import logging
import pandas as pd
import json

def load_config():
    load_dotenv()
    cfg = {
        "ALPACA_API_KEY": os.getenv("ALPACA_API_KEY"),
        "ALPACA_SECRET_KEY": os.getenv("ALPACA_SECRET_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "USE_GPT": os.getenv("USE_GPT", "false").lower() == "true",
        "USE_RSI": os.getenv("USE_RSI", "false").lower() == "true",
        "USE_STOP_LOSS": os.getenv("USE_STOP_LOSS", "true").lower() == "true",
        "STOP_LOSS_PERCENT": float(os.getenv("STOP_LOSS_PERCENT", "3.0")),
        "TAKE_PROFIT_PERCENT": float(os.getenv("TAKE_PROFIT_PERCENT", "5.0")),
        "STOCK_SYMBOLS": [s.strip().upper() for s in os.getenv("STOCK_SYMBOLS", "").split(",") if s.strip()],
        "LOOP_INTERVAL_MINUTES": float(os.getenv("LOOP_INTERVAL_MINUTES", "5")),
        "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN"),
        "DISCORD_CHANNEL_ID": os.getenv("DISCORD_CHANNEL_ID"),
        "DISCORD_ROLE_ID": os.getenv("DISCORD_ROLE_ID"),
        "DISCORD_HOLDINGS_CHANNEL_ID": os.getenv("DISCORD_HOLDINGS_CHANNEL_ID"),
        "FORCE_BUY_MODE": os.getenv("FORCE_BUY_MODE", "false").lower() == "true",
        "TRADE_BUFFER_SECONDS": float(os.getenv("TRADE_BUFFER_SECONDS", "5"))
    }
    if not cfg["ALPACA_API_KEY"] or not cfg["ALPACA_SECRET_KEY"]:
        raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
    return cfg

config = load_config()
openai.api_key = config["OPENAI_API_KEY"]
api = tradeapi.REST(config["ALPACA_API_KEY"], config["ALPACA_SECRET_KEY"], base_url="https://paper-api.alpaca.markets")

logging.basicConfig(filename='trading_bot.log', level=logging.INFO, format='%(asctime)s %(message)s')
POSITION_SIZE = 1
last_discord_message_ids = {}
HEADERS = {
    "Authorization": f"Bot {config['DISCORD_BOT_TOKEN']}",
    "Content-Type": "application/json"
}

symbol_cost_basis = {}
previous_prices = {}

def get_position_price(symbol):
    try:
        position = api.get_position(symbol)
        return float(position.avg_entry_price)
    except:
        return None

def should_stop_loss(symbol, current_price):
    entry_price = get_position_price(symbol)
    if not entry_price:
        return False
    loss = ((entry_price - current_price) / entry_price) * 100
    return loss >= config["STOP_LOSS_PERCENT"]

def should_take_profit(symbol, current_price):
    entry_price = get_position_price(symbol)
    if not entry_price:
        return False
    gain = ((current_price - entry_price) / entry_price) * 100
    return gain >= config["TAKE_PROFIT_PERCENT"]

def calc_rsi(data, period=14):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def combined_strategy(data):
    data['ema12'] = data['close'].ewm(span=12, adjust=False).mean()
    data['ema26'] = data['close'].ewm(span=26, adjust=False).mean()
    signal = "HOLD"

    if config["USE_RSI"]:
        data['rsi'] = calc_rsi(data)
        if data['rsi'].iloc[-1] < 30:
            signal = "BUY"
        elif data['rsi'].iloc[-1] > 70:
            signal = "SELL"

    if data['ema12'].iloc[-2] < data['ema26'].iloc[-2] and data['ema12'].iloc[-1] > data['ema26'].iloc[-1]:
        signal = "BUY"
    elif data['ema12'].iloc[-2] > data['ema26'].iloc[-2] and data['ema12'].iloc[-1] < data['ema26'].iloc[-1]:
        signal = "SELL"

    return signal


def ask_gpt_action(current_price, symbol):
    """Use OpenAI to suggest BUY, SELL, or HOLD."""
    prompt = (
        f"The current price of {symbol} is {current_price:.2f}. "
        "Respond with BUY, SELL, or HOLD for a short-term trade."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1,
            temperature=0,
        )
        action = response.choices[0].message["content"].strip().upper()
        if action in {"BUY", "SELL", "HOLD"}:
            return action
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
    return "HOLD"

def run_bot():
    global config
    config = load_config()  # Re-load on each loop

    print("Running bot round...")
    clock = api.get_clock()
    if not clock.is_open:
        print("Market closed. Skipping.")
        logging.info("Market closed. Skipping.")
        return

    for symbol in config["STOCK_SYMBOLS"]:
        try:
            print(f"Evaluating {symbol}...")
            bars = api.get_bars(symbol, "1Min", limit=50).df
            if bars is None or len(bars) < 30:
                print(f"Skipping {symbol}: insufficient data ({len(bars) if bars is not None else 'None'})")
                logging.warning(f"Skipping {symbol}: insufficient data ({len(bars) if bars is not None else 'None'})")
                continue

            current_price = bars['close'].iloc[-1]
            position_qty = int(api.get_position(symbol).qty) if symbol in [p.symbol for p in api.list_positions()] else 0

            if config["FORCE_BUY_MODE"]:
                action = "BUY"
            else:
                action = ask_gpt_action(current_price, symbol) if config["USE_GPT"] else combined_strategy(bars)

            if config["USE_STOP_LOSS"] and position_qty > 0 and not config["FORCE_BUY_MODE"]:
                if should_stop_loss(symbol, current_price):
                    action = "SELL"
                elif should_take_profit(symbol, current_price):
                    action = "SELL"

            if action == "BUY" and position_qty == 0:
                api.submit_order(symbol=symbol, qty=POSITION_SIZE, side='buy', type='market', time_in_force='gtc')
                logging.info(f"BUY {symbol} at ${current_price:.2f}")
            elif action == "SELL" and position_qty > 0:
                api.submit_order(symbol=symbol, qty=POSITION_SIZE, side='sell', type='market', time_in_force='gtc')
                logging.info(f"SELL {symbol} at ${current_price:.2f}")

            time.sleep(config["TRADE_BUFFER_SECONDS"])

        except Exception as e:
            logging.error(f"Error with {symbol}: {e}")
            print(f"Error with {symbol}: {e}")

if __name__ == "__main__":
    while True:
        run_bot()
        time.sleep(config["LOOP_INTERVAL_MINUTES"] * 60)

