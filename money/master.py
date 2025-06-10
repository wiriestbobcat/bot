import subprocess
import sys
from pathlib import Path

def install_requirements(bot_dir: Path) -> None:
    """Install requirements for a bot if a requirements.txt exists."""
    req_file = bot_dir / "requirements.txt"
    if req_file.exists():
        print(f"\U0001F4E6 Installing dependencies from {req_file}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            sys.exit(e.returncode)

=======

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

        install_requirements(bot_path.parent)
=======

        launch_bot(bot_path)

if __name__ == "__main__":
    main()
