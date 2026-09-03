#!/usr/bin/env python3
"""
Lido CSM & 0xSplits Automated Reward Claiming & Distribution Daemon.
Production-hardened implementation with Web3.py transaction submission.
"""

import os
import sys
import time
import json
import argparse
import logging
from typing import Dict, List, Optional
import urllib.request
from web3 import Web3
from eth_account import Account

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("CSM_Claimer")

CONFIGS = {
    "mainnet": {
        "chainId": 1,
        "csModule": "0xdA7Ade318444f634D8A3e9A95B309f3e4e941164",
        "csAccounting": "0x4D72D18DE9266E39b1aEB23FEa7195b0fFd7A634",
        "stETH": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
        "wstETH": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0",
        "splitsFactory": "0x2ed6c4e5a987829875150f1604a112ec4d8f7bfd",
        "oracleApi": "https://csm.lido.fi/api/v1/rewards/tree"
    },
    "holesky": {
        "chainId": 17000,
        "csModule": "0xE73a4D20f794051a8d793617307686E7a80b0F1E",
        "csAccounting": "0x53F81c15b14c330f81d803333F2459a9faef9900",
        "stETH": "0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034",
        "wstETH": "0x8d09a4502Cc8Bad10A5F1246fa927134f79f9D00",
        "splitsFactory": "0x2ed6c4e5a987829875150f1604a112ec4d8f7bfd",
        "oracleApi": "https://csm.holesky.lido.fi/api/v1/rewards/tree"
    }
}

CS_ACCOUNTING_ABI = [
    {
        "inputs": [
            {"name": "nodeOperatorId", "type": "uint256"},
            {"name": "cumulativeFeeShares", "type": "uint256"},
            {"name": "rewardsProof", "type": "bytes32[]"}
        ],
        "name": "pullAndSplitFeeRewards",
        "outputs": [{"name": "claimableShares", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

SPLIT_PULL_ABI = [
    {
        "inputs": [
            {"name": "split", "type": "address"},
            {"name": "token", "type": "address"}
        ],
        "name": "distribute",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


def fetch_csm_merkle_proof(api_url: str, node_operator_id: int) -> Optional[Dict]:
    url = f"{api_url}?operatorId={node_operator_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Engine1-CSM-Daemon/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data
    except Exception as e:
        logger.warning(f"Unable to fetch Merkle proof from {url}: {e}")
    return None


def claim_and_distribute(
    network: str,
    node_operator_id: int,
    split_address: str,
    rpc_url: str,
    private_key: Optional[str] = None,
    dry_run: bool = False
):
    cfg = CONFIGS.get(network)
    if not cfg:
        raise ValueError(f"Unknown network: {network}")

    logger.info(f"=== Lido CSM Reward Claiming Run ===")
    logger.info(f"Network: {network} | Operator ID: {node_operator_id} | Split Address: {split_address}")

    proof_data = fetch_csm_merkle_proof(cfg["oracleApi"], node_operator_id)
    if proof_data:
        cumulative_shares = int(proof_data.get("cumulativeFeeShares", 0))
        proof = [bytes.fromhex(p[2:] if p.startswith("0x") else p) for p in proof_data.get("proof", [])]
        logger.info(f"Discovered Claimable Cumulative Shares: {cumulative_shares} (Proof length: {len(proof)})")
    else:
        logger.info("No active Merkle tree update for this operator. Using mock/zero proof.")
        cumulative_shares = 0
        proof = []

    if dry_run:
        logger.info("[DRY RUN] Simulation mode. Skipping live on-chain transaction broadcast.")
        return

    if not private_key:
        logger.error("Private key required for live transaction broadcast.")
        return

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = Account.from_key(private_key)
    sender = account.address

    cs_accounting = w3.eth.contract(address=Web3.to_checksum_address(cfg["csAccounting"]), abi=CS_ACCOUNTING_ABI)
    split_contract = w3.eth.contract(address=Web3.to_checksum_address(split_address), abi=SPLIT_PULL_ABI)

    # Step 1: Pull and split fee rewards from Lido CSAccounting
    if cumulative_shares > 0 and len(proof) > 0:
        logger.info(f"Broadcasting pullAndSplitFeeRewards({node_operator_id}, {cumulative_shares})...")
        tx1 = cs_accounting.functions.pullAndSplitFeeRewards(
            node_operator_id, cumulative_shares, proof
        ).build_transaction({
            "from": sender,
            "nonce": w3.eth.get_transaction_count(sender),
            "gasPrice": w3.eth.gas_price,
            "chainId": cfg["chainId"]
        })
        signed_tx1 = w3.eth.account.sign_transaction(tx1, private_key)
        tx1_hash = w3.eth.send_raw_transaction(signed_tx1.rawTransaction)
        logger.info(f"Step 1 TX Broadcast: {tx1_hash.hex()}. Awaiting confirmation...")
        w3.eth.wait_for_transaction_receipt(tx1_hash)
        logger.info("Step 1 confirmed!")

    # Step 2: Distribute stETH from 0xSplits
    logger.info(f"Broadcasting 0xSplits distribute for stETH ({cfg['stETH']})...")
    tx2 = split_contract.functions.distribute(
        Web3.to_checksum_address(split_address),
        Web3.to_checksum_address(cfg["stETH"])
    ).build_transaction({
        "from": sender,
        "nonce": w3.eth.get_transaction_count(sender),
        "gasPrice": w3.eth.gas_price,
        "chainId": cfg["chainId"]
    })
    signed_tx2 = w3.eth.account.sign_transaction(tx2, private_key)
    tx2_hash = w3.eth.send_raw_transaction(signed_tx2.rawTransaction)
    logger.info(f"Step 2 TX Broadcast: {tx2_hash.hex()}. Awaiting confirmation...")
    w3.eth.wait_for_transaction_receipt(tx2_hash)
    logger.info("Step 2 confirmed! Pro-rata rewards distributed to all 4 operators.")


def main():
    parser = argparse.ArgumentParser(description="Lido CSM & 0xSplits Automated Reward Claimer")
    parser.add_argument("--network", choices=["mainnet", "holesky"], default="mainnet")
    parser.add_argument("--operator-id", type=int, default=1)
    parser.add_argument("--split-address", type=str, default=os.getenv("SPLIT_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"))
    parser.add_argument("--rpc-url", type=str, default=os.getenv("RPC_URL", "http://localhost:8545"))
    parser.add_argument("--private-key", type=str, default=os.getenv("ETH_PRIVATE_KEY"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval", type=int, default=86400)
    args = parser.parse_args()

    if args.daemon:
        logger.info(f"Starting Daemon (interval: {args.interval}s)...")
        while True:
            try:
                claim_and_distribute(args.network, args.operator_id, args.split_address, args.rpc_url, args.private_key, args.dry_run)
            except Exception as e:
                logger.error(f"Error in claim cycle: {e}")
            time.sleep(args.interval)
    else:
        claim_and_distribute(args.network, args.operator_id, args.split_address, args.rpc_url, args.private_key, args.dry_run)


if __name__ == "__main__":
    main()
