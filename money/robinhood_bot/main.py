import os
import time
import logging
import csv
import requests
from dotenv import load_dotenv
import openai
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from discord_webhook import DiscordWebhook, DiscordEmbed
import robin_stocks.robinhood as r
import threading
from concurrent.futures import ThreadPoolExecutor
import holdings  # <-- Launch holdings.py when this script is run

# Load environment variables
load_dotenv()

# Read trading strategy
strategy = int(os.getenv("TRADING_STRATEGY", 1))

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Set up OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Settings
symbol_entries = os.getenv("SYMBOLS", "BTC:crypto").split(",")
symbol_list = []
symbol_type_map = {}

for entry in symbol_entries:
    parts = entry.split(":")
    if len(parts) == 2:
        symbol, type_ = parts
    else:
        symbol, type_ = parts[0], "crypto"  # default to crypto
    symbol_list.append(symbol)
    symbol_type_map[symbol] = type_

paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
trade_amount = float(os.getenv("TRADE_AMOUNT_USD", 10))
stop_loss_pct = float(os.getenv("STOP_LOSS_PERCENT", 0.03))
take_profit_pct = float(os.getenv("TAKE_PROFIT_PERCENT", 0.05))
discord_url = os.getenv("DISCORD_WEBHOOK_URL")
alert_threshold = float(os.getenv("ALERT_THRESHOLD_PERCENT", 3.0))

# Robinhood login
robinhood_login = None
login_lock = threading.Lock()

# Price cache with expiration
price_cache = {}
CACHE_TTL = timedelta(hours=1)
CACHE_MAX_AGE = timedelta(hours=2)

# Authenticate before any threads start
def robinhood_auth():
    global robinhood_login
    with login_lock:
        if robinhood_login is None:
            try:
                robinhood_login = r.login(
                    username=os.getenv("RH_USERNAME"),
                    password=os.getenv("RH_PASSWORD"),
                    mfa_code=os.getenv("RH_MFA_CODE", None),
                    store_session=True
                )
                logging.info("✅ Logged into Robinhood.")
            except Exception as e:
                logging.error(f"🔐 Robinhood login failed: {e}")
                robinhood_login = None
        return robinhood_login

# CSV log file
log_file = "trade_log.csv"
if not os.path.exists(log_file):
    with open(log_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "symbol", "action", "price", "sma", "rsi", "macd"])

# Shared state
purchase_prices = {}
high_prices = {}
current_profit = 0.0
last_profit_date = date.today()
message_id = None
lock = threading.Lock()

# Discord status message state
last_status_message = ""

# Price SMA crossover state
previous_price_vs_sma = {}

bar_chars = ['▂','▃','▄','▅','▆','▇','█']

def calculate_indicators(prices):
    df = pd.DataFrame(prices, columns=["close"])
    df["sma"] = df["close"].rolling(window=5).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta > 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = exp1 - exp2
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    macd_value = df.iloc[-1]["macd"] - df.iloc[-1]["macd_signal"]
    crossover_icon = "📈" if macd_value > 0 else "📉"
    return df.iloc[-1]["sma"], df.iloc[-1]["rsi"], macd_value, crossover_icon

def log_trade(symbol, action, price, sma, rsi, macd):
    global current_profit
    with lock:
        if action == "buy":
            purchase_prices[symbol] = price
        elif action == "sell" and symbol in purchase_prices:
            current_profit += price - purchase_prices[symbol]
            del purchase_prices[symbol]
    with open(log_file, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), symbol, action, price, sma, rsi, macd])

def generate_price_bar(prices):
    if not prices:
        return ""
    subset = prices[-10:]
    min_price = min(subset)
    max_price = max(subset)
    scale = (max_price - min_price) / len(bar_chars) if max_price != min_price else 1
    bar = "".join(bar_chars[min(int((p - min_price) / scale), len(bar_chars) - 1)] for p in subset)
    return bar

def create_status_summary(statuses):
    message = ""
    with lock:
        for status in statuses:
            message += f"{status['symbol']} — {status['action']} @ ${status['price']:.2f} | Δ ${status['change']:.2f} ({status['change_pct']:.2f}%)\n"
            message += f"SMA: ${status['sma']:.2f} | RSI: {status['rsi']:.2f} | MACD: {status['macd']:.2f} {status['macd_icon']}\n"
            message += f"{status['price_bar']}\n"
            message += f"Chart: https://www.tradingview.com/symbols/{status['symbol']}USD/\n\n"
        message += f"**Current Profit:** ${current_profit:.2f}\n"
    return f"**Crypto Bot Update**\n\n{message}"

def create_or_update_discord_message(statuses):
    global last_status_message
    if not discord_url:
        return
    status_summary = create_status_summary(statuses)
    if status_summary == last_status_message:
        return
    last_status_message = status_summary
    try:
        webhook = DiscordWebhook(url=discord_url, content=status_summary)
        webhook.execute()
    except Exception as e:
        logging.error(f"Failed to send/update Discord message: {e}")

def send_discord_notification(message):
    if discord_url:
        try:
            webhook = DiscordWebhook(url=discord_url, content=message)
            webhook.execute()
        except Exception as e:
            logging.error(f"Failed to send Discord notification: {e}")

def get_price_data(symbol):
    symbol_type = symbol_type_map.get(symbol, "crypto")
    try:
        now = datetime.now(timezone.utc)
        keys_to_delete = [k for k, v in price_cache.items() if now - v['timestamp'] > CACHE_MAX_AGE]
        for k in keys_to_delete:
            del price_cache[k]

        if symbol in price_cache:
            cached = price_cache[symbol]
            if now - cached['timestamp'] < CACHE_TTL:
                return cached['current_price'], cached['prices']

        prices = []
        if symbol_type == "crypto":
            data = r.crypto.get_crypto_historicals(symbol, interval='5minute', span='week')
            if not data:
                raise ValueError("Empty response from Robinhood crypto historicals")
            for p in data:
                close_price = p.get("close_price")
                if close_price not in (None, ""):
                    prices.append(float(close_price))
            quote = r.crypto.get_crypto_quote(symbol)
            mark_price = quote.get('mark_price')
        else:
            data = r.stocks.get_stock_historicals(symbol, interval='5minute', span='day')
            if not data:
                raise ValueError("Empty response from Robinhood stock historicals")
            for p in data:
                close_price = p.get("close_price")
                if close_price not in (None, ""):
                    prices.append(float(close_price))
            mark_price = r.stocks.get_latest_price(symbol)[0]

        current_price = float(mark_price)
        price_cache[symbol] = {'current_price': current_price, 'prices': prices, 'timestamp': now}
        return current_price, prices
    except Exception as e:
        logging.error(f"Error fetching price data for {symbol} from Robinhood: {e}")
        return None, []

def fetch_status_for_symbol(price_tuple):
    if len(price_tuple) != 3:
        return None
    symbol, current_price, prices = price_tuple
    if not prices:
        return None

    sma, rsi, macd, macd_icon = calculate_indicators(prices)
    price_bar = generate_price_bar(prices)
    action = "hold"
    change = current_price - prices[-2]
    change_pct = (change / prices[-2]) * 100 if prices[-2] else 0

    if strategy == 1:
        if current_price > sma and rsi < 70 and macd > 0:
            action = "buy"
        elif current_price < sma and rsi > 30 and macd < 0:
            action = "sell"
    elif strategy == 2:
        if current_price > sma:
            action = "buy"
        else:
            action = "sell"

    log_trade(symbol, action, current_price, sma, rsi, macd)

    return {
        "symbol": symbol,
        "price": current_price,
        "sma": sma,
        "rsi": rsi,
        "macd": macd,
        "macd_icon": macd_icon,
        "price_bar": price_bar,
        "action": action,
        "change": change,
        "change_pct": change_pct,
    }

if __name__ == "__main__":
    robinhood_auth()
    with ThreadPoolExecutor(max_workers=len(symbol_list)) as executor:
        while True:
            load_dotenv(override=True)
            strategy = int(os.getenv("TRADING_STRATEGY", 1))

            now = datetime.now(timezone.utc).astimezone()  # local time with tzinfo
            
            # Only sleep if there are stocks and market is closed; crypto runs 24/7
            if any(symbol_type_map.get(sym, "crypto") == "stock" for sym in symbol_list):
                if now.hour < 9 or now.hour > 16:
                    logging.info("Stock market closed. Sleeping 5 minutes.")
                    time.sleep(300)
                    continue

            price_data = []
            for symbol in symbol_list:
                logging.info(f"📊 Fetching price data for {symbol}")
                current_price, prices = get_price_data(symbol)
                if current_price is not None and prices:
                    logging.info(f"✅ {symbol}: Got {len(prices)} prices, Current Price: {current_price}")
                    price_data.append((symbol, current_price, prices))
                else:
                    logging.warning(f"⚠️ {symbol}: Missing or invalid price data")

            results = list(executor.map(fetch_status_for_symbol, price_data))

            statuses = [res for res in results if res is not None]
            create_or_update_discord_message(statuses)
            time.sleep(300)
            if not statuses:
                logging.info("No valid statuses to report.")
                continue
