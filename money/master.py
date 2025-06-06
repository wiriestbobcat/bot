import subprocess
import sys
import subprocess
from pathlib import Path


def _ensure_pip() -> bool:
    """Ensure pip is available for the current interpreter."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL)
        return True
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"], stdout=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"❌ pip not available: {e}")
            return False


def install_requirements(bot_dir: Path) -> None:
    """Install dependencies from a bot's requirements.txt if present."""
    req_file = bot_dir / "requirements.txt"
    if not req_file.exists():
        print(f"\u26A0\uFE0F No requirements found at {req_file}")
        return

    print(f"\U0001F4E6 Installing dependencies from {req_file}")
    if not _ensure_pip():
        print("⚠️ Skipping install because pip is not available.")
        return
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies from {req_file}: {e}")


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
        launch_bot(bot_path)


if __name__ == "__main__":
    main()
