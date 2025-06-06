import subprocess
import os

base = r"C:\Users\willi\Desktop\viben coden\money"

bots = [
    ["python", os.path.join(base, "robinhood_bot", "main.py")],
    ["python", os.path.join(base, "alpaca_bot", "main.py")],
    # remove when headace gone ["python", os.path.join(base, "solana_staking_bot", "main.py")]
]

for bot in bots:
    print(f"✅ Launching: {' '.join(bot)}")
    try:
        subprocess.Popen(bot)
    except Exception as e:
        print(f"❌ Failed to launch: {' '.join(bot)} | {e}")
