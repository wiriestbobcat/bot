import os
import csv
import time
from datetime import datetime
import matplotlib.pyplot as plt
import robin_stocks.robinhood as r
from dotenv import load_dotenv
from discord_webhook import DiscordWebhook

load_dotenv()

chart_file = "holdings_chart.png"
gain_chart_file = "holdings_gain_chart.png"
csv_file = "holdings_history.csv"
log_file = "trade_log.csv"
discord_url = os.getenv("DISCORD_WEBHOOK_URL")
symbol_list = os.getenv("CRYPTO_SYMBOLS", "BTC").split(",")

# Authenticate with Robinhood
r.login(
    os.getenv("RH_USERNAME"),
    os.getenv("RH_PASSWORD"),
    mfa_code=os.getenv("RH_MFA_CODE", None)
)

last_message_id = None

initial_value = None

def get_total_value():
    total = 0.0
    for symbol in symbol_list:
        try:
            balance = r.crypto.get_crypto_positions()
            for b in balance:
                if b['currency']['code'] == symbol.upper():
                    qty = float(b['quantity'])
                    price = float(r.crypto.get_crypto_quote(symbol)['mark_price'])
                    total += qty * price
        except:
            continue
    return total

def append_to_csv(value):
    with open(csv_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), value])

def load_history():
    times, values = [], []
    if not os.path.exists(csv_file):
        return times, values
    with open(csv_file, mode="r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 2:
                continue
            try:
                times.append(datetime.fromisoformat(row[0]))
                values.append(float(row[1]))
            except:
                continue
    return times, values

def load_trade_annotations():
    annotations = []
    if not os.path.exists(log_file):
        return annotations
    with open(log_file, mode="r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.fromisoformat(row['timestamp'])
                label = f"{row['action'].upper()} {row['symbol']}\n${float(row['price']):.2f}"
                annotations.append((ts, label))
            except:
                continue
    return annotations

def plot_chart(times, values):
    plt.figure(figsize=(12, 5))
    plt.plot(times, values, marker='o', linestyle='-', color='green')
    plt.title("Total Crypto Holdings Over Time")
    plt.xlabel("Time")
    plt.ylabel("USD Value")
    plt.xticks(rotation=45)
    plt.grid(True)
    annotations = load_trade_annotations()
    for ts, label in annotations:
        if ts in times:
            idx = times.index(ts)
            plt.annotate(label, (times[idx], values[idx]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, color='blue', arrowprops=dict(arrowstyle='->', color='blue'))
    plt.tight_layout()
    plt.savefig(chart_file)
    plt.close()

def plot_gain_chart(times, values):
    if not values:
        return
    base = values[0]
    gains = [v - base for v in values]
    plt.figure(figsize=(12, 5))
    plt.plot(times, gains, marker='o', linestyle='-', color='blue')
    plt.title("Net Gain/Loss from Start")
    plt.xlabel("Time")
    plt.ylabel("Net USD Gain")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(gain_chart_file)
    plt.close()

def send_chart_to_discord():
    global last_message_id
    if not discord_url:
        return
    try:
        webhook = DiscordWebhook(url=discord_url)
        if last_message_id:
            webhook.set_content("[updating chart...]")
            webhook.id = last_message_id
            webhook.edit()
        with open(chart_file, "rb") as f:
            webhook.add_file(file=f.read(), filename=chart_file)
        with open(gain_chart_file, "rb") as f:
            webhook.add_file(file=f.read(), filename=gain_chart_file)
        response = webhook.execute()
        if response.ok:
            last_message_id = webhook.id
    except Exception as e:
        print(f"Failed to send chart to Discord: {e}")

if __name__ == "__main__":
    holdings  # ensure side effects (e.g. boot logic) run if applicable
    while True:
        total = get_total_value()
        append_to_csv(total)
        times, values = load_history()
        if times and values:
            plot_chart(times, values)
            plot_gain_chart(times, values)
            send_chart_to_discord()
        time.sleep(60)
