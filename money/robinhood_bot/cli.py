import typer
from bot import run_bot
from backtest import backtest
from plot import plot_chart

app = typer.Typer()

@app.command()
def live():
    """Run live/paper trading bot."""
    run_bot()

@app.command()
def test(csv_path: str = "historical_prices.csv"):
    """Run backtest on CSV."""
    backtest(csv_path)

@app.command()
def visualize(csv_path: str = "historical_prices.csv"):
    """Plot price and indicators from CSV."""
    plot_chart(csv_path)

if __name__ == "__main__":
    app()
