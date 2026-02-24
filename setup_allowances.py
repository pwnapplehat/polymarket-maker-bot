#!/usr/bin/env python3
"""
CRITICAL: Set token allowances for MetaMask/EOA wallets.

YOU MUST RUN THIS BEFORE LIVE TRADING or orders will fail with "insufficient allowance" errors.

This is ONLY needed for MetaMask/hardware wallets. Email/Magic wallets handle this automatically.
"""
import sys
from web3 import Web3
from eth_account import Account
from config import Config
from logger import logger

# Polygon Mainnet Token Addresses (VERIFIED FROM OFFICIAL DOCS)
USDC_TOKEN = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CONDITIONAL_TOKEN = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

# Exchange Contract Addresses (VERIFIED FROM OFFICIAL DOCS)
EXCHANGE_CONTRACT = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_CTF = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"

# ERC20 ABI (approve function only)
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

def setup_allowances():
    """Set token allowances for trading contracts."""
    
    if not Config.PRIVATE_KEY:
        logger.error("PRIVATE_KEY not set in .env file")
        logger.error("Please add your MetaMask private key to .env")
        sys.exit(1)
    
    # Connect to Polygon
    w3 = Web3(Web3.HTTPProvider(Config.POLYGON_RPC))
    
    if not w3.is_connected():
        logger.error(f"Failed to connect to Polygon RPC: {Config.POLYGON_RPC}")
        sys.exit(1)
    
    logger.info(f"✅ Connected to Polygon (Block: {w3.eth.block_number})")
    
    # Load wallet
    account = Account.from_key(Config.PRIVATE_KEY)
    wallet_address = account.address
    
    logger.info(f"Wallet: {wallet_address}")
    
    # Check balance
    balance_wei = w3.eth.get_balance(wallet_address)
    balance_matic = w3.from_wei(balance_wei, 'ether')
    
    logger.info(f"MATIC Balance: {balance_matic:.4f} MATIC")
    
    if balance_matic < 0.01:
        logger.warning("⚠️  Low MATIC balance! You need MATIC for gas fees.")
        logger.warning("   Get MATIC from a Polygon faucet or exchange")
    
    # Approval amount (maximum uint256)
    max_approval = 2**256 - 1
    
    # Contracts to approve
    contracts = [
        ("Exchange", EXCHANGE_CONTRACT),
        ("Neg Risk CTF", NEG_RISK_CTF),
        ("Neg Risk Adapter", NEG_RISK_ADAPTER)
    ]
    
    # Tokens to approve
    tokens = [
        ("USDC", USDC_TOKEN),
        ("Conditional Token", CONDITIONAL_TOKEN)
    ]
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Setting Token Allowances")
    logger.info("=" * 60)
    logger.info("This will submit 6 transactions (3 contracts × 2 tokens)")
    logger.info("Each transaction requires gas (typically ~0.01 MATIC)")
    logger.info("=" * 60)
    logger.info("")
    
    input("Press ENTER to continue or Ctrl+C to cancel... ")
    
    total_txns = 0
    
    for token_name, token_address in tokens:
        logger.info("")
        logger.info(f"Processing {token_name} ({token_address[:8]}...)")
        
        token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        for contract_name, contract_address in contracts:
            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                wallet_address,
                contract_address
            ).call()
            
            if current_allowance >= max_approval // 2:
                logger.info(f"  ✅ {contract_name}: Already approved")
                continue
            
            logger.info(f"  📝 {contract_name}: Setting allowance...")
            
            try:
                # Build transaction
                txn = token_contract.functions.approve(
                    contract_address,
                    max_approval
                ).build_transaction({
                    'from': wallet_address,
                    'nonce': w3.eth.get_transaction_count(wallet_address),
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price
                })
                
                # Sign transaction
                signed_txn = account.sign_transaction(txn)
                
                # Send transaction
                tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                
                logger.info(f"     TX: {tx_hash.hex()}")
                logger.info(f"     Waiting for confirmation...")
                
                # Wait for receipt
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    logger.info(f"  ✅ {contract_name}: Approved!")
                    total_txns += 1
                else:
                    logger.error(f"  ❌ {contract_name}: Transaction failed")
                
            except Exception as e:
                logger.error(f"  ❌ {contract_name}: {e}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"✅ Setup Complete! ({total_txns} transactions confirmed)")
    logger.info("=" * 60)
    logger.info("")
    logger.info("You can now trade on Polymarket:")
    logger.info("  python bot.py          # Dry-run mode")
    logger.info("  python bot.py --live   # Live trading")
    logger.info("")

if __name__ == "__main__":
    setup_allowances()
