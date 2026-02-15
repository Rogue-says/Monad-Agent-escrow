#!/usr/bin/env python3
"""
Monad Escrow Integration Script for OpenClaw Skill
Handles job posting and escrow management on Monad Testnet
"""

import os
import json
import time
from typing import Dict, Optional, Tuple
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MonadEscrowClient:
    """Client for interacting with Monad escrow contracts"""
    
    def __init__(self, private_key: str, rpc_url: str = "https://testnet-rpc.monad.xyz/"):
        """
        Initialize Monad Escrow Client
        
        Args:
            private_key: Private key of the account
            rpc_url: RPC endpoint URL (defaults to Monad testnet)
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Verify connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {rpc_url}")
        
        # Setup account
        self.account: LocalAccount = Account.from_key(private_key)
        self.address = self.account.address
        
        # Network configuration
        self.chain_id = 10143  # Monad testnet
        self.gas_price = 52000000000  # 52 gwei
        
        # Contract ABI (simplified - use full ABI in production)
        self.escrow_factory_abi = json.loads('''[
            {
                "inputs": [
                    {"internalType": "uint256", "name": "jobId", "type": "uint256"},
                    {"internalType": "address", "name": "_worker", "type": "address"},
                    {"internalType": "uint256", "name": "_amount", "type": "uint256"}
                ],
                "name": "createEscrow",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}],
                "name": "getEscrow",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getEscrowCount",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "anonymous": false,
                "inputs": [
                    {"indexed": true, "internalType": "uint256", "name": "jobId", "type": "uint256"},
                    {"indexed": true, "internalType": "address", "name": "escrowAddress", "type": "address"},
                    {"indexed": true, "internalType": "address", "name": "creator", "type": "address"},
                    {"indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "EscrowCreated",
                "type": "event"
            }
        ]''')
        
        self.escrow_factory_address = None
        
    def set_factory_address(self, address: str) -> None:
        """Set the EscrowFactory contract address"""
        if not Web3.is_address(address):
            raise ValueError(f"Invalid contract address: {address}")
        self.escrow_factory_address = Web3.to_checksum_address(address)
    
    def get_balance(self) -> str:
        """Get account balance in MON"""
        balance_wei = self.w3.eth.get_balance(self.address)
        balance_mon = self.w3.from_wei(balance_wei, "ether")
        return str(balance_mon)
    
    def post_job(
        self,
        job_id: int,
        worker_address: str,
        budget_in_mon: float,
        job_data: Optional[Dict] = None
    ) -> Dict:
        """
        Post a job and create an escrow contract
        
        Args:
            job_id: Unique job identifier
            worker_address: Address of the worker
            budget_in_mon: Budget in MON tokens
            job_data: Additional job metadata (optional)
        
        Returns:
            Dictionary with transaction hash and escrow address
        """
        if self.escrow_factory_address is None:
            raise ValueError("EscrowFactory address not set")
        
        if not Web3.is_address(worker_address):
            raise ValueError(f"Invalid worker address: {worker_address}")
        
        if budget_in_mon <= 0:
            raise ValueError("Budget must be greater than 0")
        
        # Convert MON to wei
        amount_wei = self.w3.to_wei(budget_in_mon, "ether")
        worker_address = Web3.to_checksum_address(worker_address)
        
        try:
            # Get factory contract
            factory = self.w3.eth.contract(
                address=self.escrow_factory_address,
                abi=self.escrow_factory_abi
            )
            
            # Build transaction
            print(f"📝 Building transaction for job {job_id}...")
            print(f"   Worker: {worker_address}")
            print(f"   Budget: {budget_in_mon} MON")
            
            txn = factory.functions.createEscrow(
                job_id,
                worker_address,
                amount_wei
            ).build_transaction({
                'from': self.address,
                'value': amount_wei,
                'gas': 300000,
                'gasPrice': self.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'chainId': self.chain_id
            })
            
            # Sign transaction
            print("🔏 Signing transaction...")
            signed_txn = self.account.sign_transaction(txn)
            
            # Send transaction
            print("📤 Sending transaction to Monad...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            
            print(f"✅ Transaction sent: {tx_hash_hex}")
            
            # Wait for receipt
            print("⏳ Waiting for confirmation...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] == 1:
                print(f"✔️ Transaction confirmed in block {receipt['blockNumber']}")
                
                # Get escrow address from logs
                escrow_address = self._extract_escrow_address_from_receipt(receipt, factory)
                
                result = {
                    "status": "success",
                    "job_id": job_id,
                    "tx_hash": tx_hash_hex,
                    "block_number": receipt['blockNumber'],
                    "gas_used": receipt['gasUsed'],
                    "escrow_address": escrow_address,
                    "job_data": job_data or {}
                }
                
                print(f"🎉 Escrow created at: {escrow_address}")
                return result
            else:
                raise Exception("Transaction failed")
            
        except Exception as e:
            print(f"❌ Error posting job: {str(e)}")
            raise
    
    def get_escrow_address(self, job_id: int) -> Optional[str]:
        """Get escrow contract address for a job"""
        if self.escrow_factory_address is None:
            raise ValueError("EscrowFactory address not set")
        
        try:
            factory = self.w3.eth.contract(
                address=self.escrow_factory_address,
                abi=self.escrow_factory_abi
            )
            
            escrow_address = factory.functions.getEscrow(job_id).call()
            
            if escrow_address == "0x0000000000000000000000000000000000000000":
                return None
            
            return escrow_address
        
        except Exception as e:
            print(f"❌ Error getting escrow: {str(e)}")
            return None
    
    def get_factory_escrow_count(self) -> int:
        """Get total number of escrows created"""
        if self.escrow_factory_address is None:
            raise ValueError("EscrowFactory address not set")
        
        try:
            factory = self.w3.eth.contract(
                address=self.escrow_factory_address,
                abi=self.escrow_factory_abi
            )
            
            count = factory.functions.getEscrowCount().call()
            return int(count)
        
        except Exception as e:
            print(f"❌ Error getting escrow count: {str(e)}")
            return 0
    
    def _extract_escrow_address_from_receipt(self, receipt, factory):
        """Extract escrow address from transaction receipt logs"""
        try:
            # Decode logs to find EscrowCreated event
            logs = factory.events.EscrowCreated().process_receipt(receipt)
            if logs:
                return logs[0]['args']['escrowAddress']
        except Exception as e:
            print(f"Warning: Could not extract escrow from logs: {str(e)}")
        
        return None


def main():
    """Example usage of MonadEscrowClient"""
    
    # Get credentials from environment
    private_key = os.getenv("PRIVATE_KEY")
    factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
    
    if not private_key:
        print("❌ Error: PRIVATE_KEY not found in environment variables")
        print("   Set it using: export PRIVATE_KEY=your_private_key")
        return
    
    if not factory_address:
        print("❌ Error: ESCROW_FACTORY_ADDRESS not found in environment variables")
        print("   Set it using: export ESCROW_FACTORY_ADDRESS=0x...")
        return
    
    try:
        # Initialize client
        print("🔌 Connecting to Monad Testnet...")
        client = MonadEscrowClient(private_key)
        client.set_factory_address(factory_address)
        
        # Check balance
        balance = client.get_balance()
        print(f"💰 Account balance: {balance} MON")
        
        # Example: Post a job
        print("\n📋 Creating a test job...")
        job_id = int(time.time())
        worker_address = "0x742d35Cc6634C0532925a3b844Bc0c6Ea17e3d6B"  # Replace with actual worker
        budget = 0.1  # 0.1 MON
        
        result = client.post_job(
            job_id=job_id,
            worker_address=worker_address,
            budget_in_mon=budget,
            job_data={
                "title": "Test Job",
                "description": "A test job for Monad escrow"
            }
        )
        
        print("\n✅ Job posted successfully!")
        print(json.dumps(result, indent=2))
        
        # Get escrow count
        count = client.get_factory_escrow_count()
        print(f"\n📊 Total escrows created: {count}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
