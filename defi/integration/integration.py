"""
FNTX Blockchain Integration

Handles interaction with FNTX smart contracts from Python.
"""

import os
import json
from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

class FNTXBlockchain:
    """Main interface for interacting with FNTX blockchain contracts"""
    
    def __init__(self, 
                 rpc_url: str = None,
                 private_key: str = None,
                 network: str = "polygon"):
        """
        Initialize blockchain connection
        
        Args:
            rpc_url: RPC endpoint URL (defaults to Polygon RPC)
            private_key: Private key for transactions
            network: Network name (polygon or mumbai)
        """
        # Set RPC URL
        if rpc_url:
            self.rpc_url = rpc_url
        elif network == "polygon":
            self.rpc_url = "https://polygon-rpc.com"
        elif network == "mumbai":
            self.rpc_url = "https://rpc-mumbai.maticvigil.com"
        else:
            raise ValueError(f"Unknown network: {network}")
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Add POA middleware for Polygon
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        # Check connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {network}")
        
        # Set up account if private key provided
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        
        # Load contract ABIs and addresses
        self.contracts = self._load_contracts(network)
        
    def _load_contracts(self, network: str) -> Dict:
        """Load contract ABIs and addresses from deployment files"""
        contracts = {}
        
        # Load deployment info
        deployment_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "deployments", 
            f"{network}.json"
        )
        
        if os.path.exists(deployment_path):
            with open(deployment_path, 'r') as f:
                deployment = json.load(f)
            
            # Load FNTX token
            fntx_abi = self._load_abi("FNTX")
            contracts['FNTX'] = self.w3.eth.contract(
                address=deployment['contracts']['FNTX']['address'],
                abi=fntx_abi
            )
            
            # Load TrackRecord
            track_record_abi = self._load_abi("TrackRecord")
            contracts['TrackRecord'] = self.w3.eth.contract(
                address=deployment['contracts']['TrackRecord']['proxy'],
                abi=track_record_abi
            )
        
        return contracts
    
    def _load_abi(self, contract_name: str) -> List:
        """Load contract ABI from artifacts"""
        artifact_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "contracts",
            f"{contract_name}.sol",
            f"{contract_name}.json"
        )
        
        if os.path.exists(artifact_path):
            with open(artifact_path, 'r') as f:
                artifact = json.load(f)
                return artifact['abi']
        
        return []
    
    def get_fntx_balance(self, address: str = None) -> Decimal:
        """
        Get FNTX token balance for an address
        
        Args:
            address: Address to check (defaults to connected account)
            
        Returns:
            Balance in FNTX tokens
        """
        if not address and self.account:
            address = self.account.address
        
        if not address:
            raise ValueError("No address provided")
        
        balance = self.contracts['FNTX'].functions.balanceOf(address).call()
        return Decimal(balance) / Decimal(10**18)
    
    def get_burn_amount(self) -> Decimal:
        """Get current burn amount required to post a record"""
        amount = self.contracts['TrackRecord'].functions.burnAmount().call()
        return Decimal(amount) / Decimal(10**18)
    
    def approve_fntx(self, amount: Decimal) -> str:
        """
        Approve FNTX tokens for TrackRecord contract
        
        Args:
            amount: Amount of FNTX to approve
            
        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("No account configured")
        
        # Convert to wei
        amount_wei = int(amount * Decimal(10**18))
        
        # Build transaction
        tx = self.contracts['FNTX'].functions.approve(
            self.contracts['TrackRecord'].address,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()
    
    def post_daily_record(self, date: int, ipfs_hash: str) -> str:
        """
        Post a daily trading record to the blockchain
        
        Args:
            date: Date in YYYYMMDD format (e.g., 20240115)
            ipfs_hash: IPFS hash of the trading data
            
        Returns:
            Transaction hash
        """
        if not self.account:
            raise ValueError("No account configured")
        
        # Convert IPFS hash to bytes32
        data_hash = Web3.keccak(text=ipfs_hash)
        
        # Check if user has approved enough FNTX
        burn_amount = self.get_burn_amount()
        allowance = self.contracts['FNTX'].functions.allowance(
            self.account.address,
            self.contracts['TrackRecord'].address
        ).call()
        
        if Decimal(allowance) / Decimal(10**18) < burn_amount:
            # Need to approve first
            print(f"Approving {burn_amount} FNTX...")
            approve_tx = self.approve_fntx(burn_amount * 2)  # Approve double for convenience
            print(f"Approval tx: {approve_tx}")
            # Wait for confirmation
            self.w3.eth.wait_for_transaction_receipt(approve_tx)
        
        # Build transaction
        tx = self.contracts['TrackRecord'].functions.postDailyRecord(
            date,
            data_hash
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"Record posted! TX: {tx_hash.hex()}")
        print(f"Burned {burn_amount} FNTX")
        
        return tx_hash.hex()
    
    def get_record(self, trader: str, date: int) -> Optional[str]:
        """
        Get a trader's record for a specific date
        
        Args:
            trader: Trader's address
            date: Date in YYYYMMDD format
            
        Returns:
            IPFS hash or None if no record
        """
        data_hash = self.contracts['TrackRecord'].functions.getRecord(
            trader, 
            date
        ).call()
        
        if data_hash == b'\x00' * 32:
            return None
        
        # TODO: Convert back from bytes32 to IPFS hash
        return data_hash.hex()
    
    def get_record_range(self, trader: str, start_date: int, end_date: int) -> List[Optional[str]]:
        """
        Get a trader's records for a date range
        
        Args:
            trader: Trader's address
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            List of IPFS hashes
        """
        hashes = self.contracts['TrackRecord'].functions.getRecordRange(
            trader,
            start_date,
            end_date
        ).call()
        
        records = []
        for h in hashes:
            if h == b'\x00' * 32:
                records.append(None)
            else:
                records.append(h.hex())
        
        return records
    
    def estimate_gas_cost(self) -> Dict[str, Decimal]:
        """Estimate gas costs for posting a record"""
        gas_price = self.w3.eth.gas_price
        
        # Estimate gas for posting record (typical is ~100k gas)
        estimated_gas = 100000
        
        # Calculate costs
        gas_cost_wei = gas_price * estimated_gas
        gas_cost_matic = Decimal(gas_cost_wei) / Decimal(10**18)
        
        # Assume MATIC = $0.80 (you'd want to fetch real price)
        gas_cost_usd = gas_cost_matic * Decimal("0.80")
        
        return {
            'gas_price_gwei': Decimal(gas_price) / Decimal(10**9),
            'estimated_gas': estimated_gas,
            'cost_matic': gas_cost_matic,
            'cost_usd': gas_cost_usd
        }