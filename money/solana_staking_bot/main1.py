import requests
import time
import json
from web3 import Web3

# Lido contract address and ABI for stETH
LIDO_CONTRACT_ADDRESS = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
LIDO_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_addr", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getTotalPooledEther",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [],
        "name": "submit",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": True,
        "type": "function"
    }
]

# Set your Ethereum address, private key, and Web3 provider
YOUR_ETH_ADDRESS = "0xd5ED4B8e20E5075F5272ef386a6286CD55E0BD13"
PRIVATE_KEY = "ce6b71aa57c97534f363ca1fa899203acece0f4c88fa84fbaa2926d8ac606b13"
WEB3_PROVIDER_URL = "https://mainnet.infura.io/v3/4205165ab6b5480eb3a801996fb1e52e"

web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if web3.is_connected():
    print("✅ Connected to Ethereum node.")
else:
    print("❌ Failed to connect to Ethereum node.")

lido_contract = web3.eth.contract(address=Web3.to_checksum_address(LIDO_CONTRACT_ADDRESS), abi=LIDO_ABI)

# Fetch ETH price using CoinGecko
def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "ethereum", "vs_currencies": "usd"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data["ethereum"]["usd"]
    except Exception as e:
        print(f"Error fetching ETH price: {e}")
        return None

# Get stETH balance for user
def get_steth_balance():
    try:
        balance = lido_contract.functions.balanceOf(Web3.to_checksum_address(YOUR_ETH_ADDRESS)).call()
        return web3.from_wei(balance, 'ether')
    except Exception as e:
        print(f"Error fetching stETH balance: {e}")
        return None

# Get total pooled ETH in Lido
def get_total_pooled_eth():
    try:
        total = lido_contract.functions.getTotalPooledEther().call()
        return web3.from_wei(total, 'ether')
    except Exception as e:
        print(f"Error fetching total pooled ETH: {e}")
        return None

# Automatically stake available ETH
def auto_stake_eth():
    try:
        balance = web3.eth.get_balance(YOUR_ETH_ADDRESS)
        eth_to_stake = balance - web3.to_wei(0.01, 'ether')  # leave some for gas
        if eth_to_stake <= 0:
            print("⚠️ Not enough ETH to stake.")
            return

        nonce = web3.eth.get_transaction_count(YOUR_ETH_ADDRESS)
        txn = lido_contract.functions.submit().build_transaction({
            'from': YOUR_ETH_ADDRESS,
            'value': eth_to_stake,
            'gas': 200000,
            'gasPrice': web3.to_wei('30', 'gwei'),
            'nonce': nonce
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"🚀 Staking transaction sent! TX Hash: {web3.to_hex(tx_hash)}")

    except Exception as e:
        print(f"❌ Error staking ETH: {e}")

# Main staking bot loop
def staking_bot_loop():
    print("🔄 Entered staking bot loop...")
    while True:
        eth_price = get_eth_price()
        steth_balance = get_steth_balance()
        pooled_eth = get_total_pooled_eth()

        if eth_price and steth_balance is not None and pooled_eth is not None:
            value_usd = steth_balance * eth_price
            print(f"✅ ETH Price: ${eth_price}")
            print(f"🔐 Your stETH Balance: {steth_balance:.4f} stETH (~${value_usd:.2f})")
            print(f"🌊 Total ETH staked via Lido: {pooled_eth:.2f} ETH")
            auto_stake_eth()
        else:
            print("❌ Failed to fetch one or more staking metrics.")

        time.sleep(300)  # wait 5 minutes

if __name__ == "__main__":
    print("🔄 Starting staking bot loop...")
    try:
        staking_bot_loop()
    except Exception as e:
        print(f"❌ Fatal error in staking bot loop: {e}")
