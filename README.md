# Trading Bots

This repository contains a collection of simple trading bots and a launcher script.

## Bots
- **alpaca_bot** – trades stocks via Alpaca. Requires an Alpaca API key and, if enabled, an OpenAI key.
- **robinhood_bot** – trades crypto or stocks on Robinhood.
- **solana_staking_bot** – stakes ETH via Lido. Credentials are loaded from environment variables.

## Setup
1. Install Python. `pip` is recommended but the `run` script will try to
   bootstrap it automatically if it's missing.
2. Either install dependencies yourself or use the provided `run` launcher.
   - Manual install:
     ```bash
     pip install -r money/alpaca_bot/requirements.txt
     pip install -r money/robinhood_bot/requirements.txt
     ```
   - Or simply run `./run` (or `python run`) which installs the requirements and starts the bots.
3. Copy `.env.example` to `.env` and fill in the required values, or otherwise
   set these environment variables:
   - `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `OPENAI_API_KEY`
   - `RH_USERNAME`, `RH_PASSWORD`, `RH_MFA_CODE`
   - `ETH_ADDRESS`, `PRIVATE_KEY`, `WEB3_PROVIDER_URL`
4. Run the launcher directly or via the helper script:
   ```bash
   python money/master.py     # manual run
   # or
   ./run                      # installs deps and runs both bots
   ```

## License

This project is released under the MIT License.
