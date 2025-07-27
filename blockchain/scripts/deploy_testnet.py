"""
Deploy FNTX contracts to testnet (Mumbai or Sepolia)

This script deploys the token and track record contracts to testnet for testing.
"""

import os
import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestnetDeployer:
    """Deploy contracts to testnet"""
    
    def __init__(self, network='mumbai'):
        self.network = network
        self.setup_network()
        self.setup_account()
    
    def setup_network(self):
        """Setup network connection"""
        
        if self.network == 'mumbai':
            # Polygon Mumbai testnet
            self.rpc_url = "https://rpc-mumbai.maticvigil.com"
            self.chain_id = 80001
            self.explorer = "https://mumbai.polygonscan.com"
            self.native_token = "MATIC"
        elif self.network == 'sepolia':
            # Ethereum Sepolia testnet
            self.rpc_url = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
            self.chain_id = 11155111
            self.explorer = "https://sepolia.etherscan.io"
            self.native_token = "ETH"
        else:
            raise ValueError(f"Unknown network: {self.network}")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.network}")
        
        print(f"Connected to {self.network} testnet")
    
    def setup_account(self):
        """Setup deployer account"""
        
        private_key = os.getenv('TESTNET_PRIVATE_KEY')
        if not private_key:
            raise ValueError("TESTNET_PRIVATE_KEY not found in environment")
        
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # Check balance
        balance = self.w3.eth.get_balance(self.address)
        balance_ether = self.w3.from_wei(balance, 'ether')
        
        print(f"Deployer address: {self.address}")
        print(f"Balance: {balance_ether} {self.native_token}")
        
        if balance == 0:
            print(f"\n⚠️  WARNING: No {self.native_token} balance!")
            print(f"Get testnet {self.native_token} from:")
            if self.network == 'mumbai':
                print("https://faucet.polygon.technology/")
            else:
                print("https://sepoliafaucet.com/")
    
    def deploy_contract(self, contract_name, *args):
        """Deploy a single contract"""
        
        # Load contract artifacts
        with open(f'../artifacts/{contract_name}.json', 'r') as f:
            contract_data = json.load(f)
        
        abi = contract_data['abi']
        bytecode = contract_data['bytecode']
        
        # Create contract instance
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Build constructor transaction
        constructor = Contract.constructor(*args)
        
        # Estimate gas
        gas_estimate = constructor.estimate_gas({'from': self.address})
        gas_price = self.w3.eth.gas_price
        
        print(f"\nDeploying {contract_name}...")
        print(f"Estimated gas: {gas_estimate:,}")
        print(f"Gas price: {self.w3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.address)
        tx = constructor.build_transaction({
            'from': self.address,
            'gas': int(gas_estimate * 1.2),  # 20% buffer
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': self.chain_id
        })
        
        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        
        # Send transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction sent: {tx_hash.hex()}")
        
        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            contract_address = receipt.contractAddress
            print(f"✅ {contract_name} deployed at: {contract_address}")
            print(f"View on explorer: {self.explorer}/address/{contract_address}")
            return contract_address
        else:
            print(f"❌ Deployment failed!")
            return None
    
    def deploy_all(self):
        """Deploy all contracts"""
        
        print(f"\n{'='*60}")
        print(f"FNTX Testnet Deployment on {self.network.upper()}")
        print(f"{'='*60}")
        
        # 1. Deploy FNTX Token
        print("\n1. Deploying FNTX Token...")
        fntx_address = self.deploy_contract('FNTX')
        
        if not fntx_address:
            print("Failed to deploy FNTX token")
            return
        
        # 2. Deploy TrackRecordV3
        print("\n2. Deploying TrackRecordV3...")
        burn_amount = self.w3.to_wei(10, 'ether')  # 10 FNTX per record
        
        # Deploy implementation
        impl_address = self.deploy_contract('TrackRecordV3')
        
        if not impl_address:
            print("Failed to deploy TrackRecordV3")
            return
        
        # Deploy proxy (would use OpenZeppelin's TransparentUpgradeableProxy)
        # For now, we'll use the implementation directly
        track_record_address = impl_address
        
        # 3. Initialize TrackRecordV3
        print("\n3. Initializing TrackRecordV3...")
        
        track_record_abi = self._load_abi('TrackRecordV3')
        track_record = self.w3.eth.contract(
            address=track_record_address,
            abi=track_record_abi
        )
        
        # Initialize with parameters
        init_tx = track_record.functions.initialize(
            fntx_address,
            burn_amount,
            "FNTX Trading Days",
            "FNTX-DAY",
            "ipfs://QmYourBaseURI/"  # Replace with actual IPFS base URI
        ).build_transaction({
            'from': self.address,
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'chainId': self.chain_id
        })
        
        signed_init = self.w3.eth.account.sign_transaction(init_tx, self.account.key)
        init_hash = self.w3.eth.send_raw_transaction(signed_init.rawTransaction)
        init_receipt = self.w3.eth.wait_for_transaction_receipt(init_hash)
        
        if init_receipt.status == 1:
            print("✅ TrackRecordV3 initialized")
        else:
            print("❌ Initialization failed")
            return
        
        # 4. Save deployment info
        deployment_info = {
            'network': self.network,
            'chainId': self.chain_id,
            'contracts': {
                'FNTX': fntx_address,
                'TrackRecordV3': track_record_address
            },
            'deployer': self.address,
            'timestamp': self.w3.eth.get_block('latest')['timestamp']
        }
        
        filename = f'deployment_{self.network}.json'
        with open(filename, 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"\n{'='*60}")
        print("✅ Deployment Complete!")
        print(f"{'='*60}")
        print(f"\nDeployment info saved to: {filename}")
        print("\nContract addresses:")
        print(f"  FNTX Token: {fntx_address}")
        print(f"  TrackRecordV3: {track_record_address}")
        print(f"\nNext steps:")
        print("1. Get testnet FNTX tokens: fntx testnet faucet")
        print("2. Test signature posting: fntx signature test --network " + self.network)
        print("3. View on explorer: " + self.explorer)
    
    def _load_abi(self, contract_name):
        """Load contract ABI"""
        with open(f'../artifacts/{contract_name}.json', 'r') as f:
            return json.load(f)['abi']


def main():
    """Main deployment function"""
    
    import argparse
    parser = argparse.ArgumentParser(description='Deploy FNTX contracts to testnet')
    parser.add_argument(
        '--network',
        choices=['mumbai', 'sepolia'],
        default='mumbai',
        help='Testnet to deploy to'
    )
    
    args = parser.parse_args()
    
    # Create .env template if it doesn't exist
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("# Testnet deployment configuration\n")
            f.write("TESTNET_PRIVATE_KEY=your_private_key_here\n")
            f.write("INFURA_KEY=your_infura_key_here\n")
        print("Created .env template. Please add your private key.")
        return
    
    # Deploy
    deployer = TestnetDeployer(args.network)
    deployer.deploy_all()


if __name__ == "__main__":
    main()