# Trading Bots

This repository contains a collection of simple trading bots and a launcher script.

## Bots
- **alpaca_bot** – trades stocks via Alpaca. Requires an Alpaca API key and, if enabled, an OpenAI key.
- **robinhood_bot** – trades crypto or stocks on Robinhood.
- **solana_staking_bot** – stakes ETH via Lido. Credentials are loaded from environment variables.

## Setup
1. Install Python and `pip`.
2. Install each bot's requirements:
   ```bash
   pip install -r money/alpaca_bot/requirements.txt
   pip install -r money/robinhood_bot/requirements.txt
   ```
3. Provide any required environment variables:
   - `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `OPENAI_API_KEY`
   - `RH_USERNAME`, `RH_PASSWORD`, `RH_MFA_CODE`
   - `ETH_ADDRESS`, `PRIVATE_KEY`, `WEB3_PROVIDER_URL`
4. Run the launcher:
   ```bash
   python money/master.py
   ```

## License

This project is released under the MIT License.
