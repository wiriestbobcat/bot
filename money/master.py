import subprocess
import sys
from pathlib import Path

def launch_bot(main_path: Path) -> None:
    """Launch a bot's main.py in a new process."""
    print(f"\u2705 Launching: {main_path}")
    try:
        subprocess.Popen([sys.executable, str(main_path)])
    except Exception as e:
        print(f"\u274C Failed to launch: {main_path} | {e}")

def main() -> None:
    base = Path(__file__).resolve().parent
    bots = [
        base / "robinhood_bot" / "main.py",
        base / "alpaca_bot" / "main.py",
    ]

    for bot_path in bots:
        launch_bot(bot_path)

if __name__ == "__main__":
    main()
