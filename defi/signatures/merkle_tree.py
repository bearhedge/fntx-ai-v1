"""
Merkle Tree Implementation for Trading Data

Creates cryptographic proof of all trading metrics.
"""

import hashlib
from typing import List, Optional, Tuple, Dict
import json


class MerkleNode:
    """Node in the Merkle tree"""
    
    def __init__(self, data: Optional[str] = None, 
                 left: Optional['MerkleNode'] = None,
                 right: Optional['MerkleNode'] = None):
        self.data = data
        self.left = left
        self.right = right
        self.hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate hash for this node"""
        
        if self.data is not None:
            # Leaf node - hash the data
            return hashlib.sha256(self.data.encode()).hexdigest()
        else:
            # Internal node - hash the concatenation of children
            left_hash = self.left.hash if self.left else ""
            right_hash = self.right.hash if self.right else ""
            combined = left_hash + right_hash
            return hashlib.sha256(combined.encode()).hexdigest()


class MerkleTree:
    """Merkle tree for trading data verification"""
    
    def __init__(self, data_elements: List[str]):
        self.leaves = [MerkleNode(data) for data in data_elements]
        self.root_node = self._build_tree(self.leaves)
        self.root = self.root_node.hash if self.root_node else ""
        
    def _build_tree(self, nodes: List[MerkleNode]) -> Optional[MerkleNode]:
        """Build the tree from leaf nodes"""
        
        if not nodes:
            return None
        
        if len(nodes) == 1:
            return nodes[0]
        
        # Build next level
        next_level = []
        
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else None
            
            # Create parent node
            if right:
                parent = MerkleNode(left=left, right=right)
            else:
                # Odd number of nodes - duplicate the last one
                parent = MerkleNode(left=left, right=left)
            
            next_level.append(parent)
        
        return self._build_tree(next_level)
    
    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for element at given index
        
        Returns list of (hash, position) tuples where position is 'left' or 'right'
        """
        
        if index < 0 or index >= len(self.leaves):
            raise ValueError(f"Index {index} out of range")
        
        proof = []
        nodes = self.leaves.copy()
        target_index = index
        
        while len(nodes) > 1:
            next_level = []
            
            for i in range(0, len(nodes), 2):
                if i == target_index or i + 1 == target_index:
                    # This pair contains our target
                    if i == target_index:
                        # Target is on the left, add right sibling to proof
                        if i + 1 < len(nodes):
                            proof.append((nodes[i + 1].hash, 'right'))
                    else:
                        # Target is on the right, add left sibling to proof
                        proof.append((nodes[i].hash, 'left'))
                    
                    # Update target index for next level
                    target_index = i // 2
                
                # Create parent (same as in build_tree)
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                parent = MerkleNode(left=left, right=right)
                next_level.append(parent)
            
            nodes = next_level
        
        return proof
    
    def verify_proof(self, element: str, index: int, proof: List[Tuple[str, str]]) -> bool:
        """Verify a Merkle proof"""
        
        # Start with the hash of the element
        current_hash = hashlib.sha256(element.encode()).hexdigest()
        
        # Apply each proof element
        for proof_hash, position in proof:
            if position == 'left':
                combined = proof_hash + current_hash
            else:
                combined = current_hash + proof_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        # Check if we end up with the root
        return current_hash == self.root


class TradingDataMerkleTree(MerkleTree):
    """Specialized Merkle tree for trading data with structured organization"""
    
    def __init__(self, trading_metrics: Dict):
        # Organize metrics into categories
        self.categories = {
            'core': ['date', 'timestamp', 'trading_day_num'],
            'account': ['opening_balance', 'closing_balance', 'deposits', 'withdrawals'],
            'pnl': ['gross_pnl', 'commissions', 'interest_expense', 'interest_accruals', 'net_pnl'],
            'trading': ['contracts_traded', 'notional_volume', 'implied_turnover', 'position_size_percentage'],
            'greeks': ['delta_exposure', 'gamma_exposure', 'theta_decay', 'vega_exposure'],
            'performance': ['win_rate_30d', 'volatility_30d', 'sharpe_ratio_30d', 'max_drawdown_30d'],
            'fund': ['dpi', 'tvpi', 'rvpi']
        }
        
        # Convert metrics to leaf data
        leaf_data = self._metrics_to_leaves(trading_metrics)
        
        super().__init__(leaf_data)
        
        # Store category roots for granular verification
        self.category_roots = self._calculate_category_roots(trading_metrics)
    
    def _metrics_to_leaves(self, metrics: Dict) -> List[str]:
        """Convert metrics dictionary to ordered leaf data"""
        
        leaves = []
        
        # Process in category order for consistency
        for category, fields in self.categories.items():
            for field in fields:
                if field in metrics:
                    value = metrics[field]
                    # Create deterministic string representation
                    leaf = f"{field}:{value}"
                    leaves.append(leaf)
        
        return leaves
    
    def _calculate_category_roots(self, metrics: Dict) -> Dict[str, str]:
        """Calculate Merkle root for each category"""
        
        category_roots = {}
        
        for category, fields in self.categories.items():
            # Get values for this category
            category_data = []
            for field in fields:
                if field in metrics:
                    value = metrics[field]
                    category_data.append(f"{field}:{value}")
            
            if category_data:
                # Build mini Merkle tree for this category
                category_tree = MerkleTree(category_data)
                category_roots[category] = category_tree.root
        
        return category_roots
    
    def get_category_proof(self, category: str) -> Dict[str, str]:
        """Get proof for a specific category of data"""
        
        if category not in self.categories:
            raise ValueError(f"Unknown category: {category}")
        
        return {
            'category': category,
            'root': self.category_roots.get(category, ''),
            'fields': self.categories[category]
        }
    
    def to_json(self) -> str:
        """Export tree structure as JSON"""
        
        tree_data = {
            'root': self.root,
            'category_roots': self.category_roots,
            'categories': self.categories,
            'leaf_count': len(self.leaves)
        }
        
        return json.dumps(tree_data, indent=2)


# Utility functions for multi-user aggregation
def aggregate_merkle_roots(user_roots: List[Tuple[str, str]]) -> str:
    """
    Aggregate multiple user Merkle roots into a single root
    
    Args:
        user_roots: List of (user_address, merkle_root) tuples
        
    Returns:
        Aggregated Merkle root
    """
    
    # Sort by user address for deterministic ordering
    sorted_roots = sorted(user_roots, key=lambda x: x[0])
    
    # Create leaves from user roots
    leaves = []
    for user_address, root in sorted_roots:
        leaf = f"{user_address}:{root}"
        leaves.append(leaf)
    
    # Build aggregation tree
    if leaves:
        agg_tree = MerkleTree(leaves)
        return agg_tree.root
    else:
        return ""


def verify_user_in_aggregation(user_address: str, 
                              user_root: str,
                              aggregated_root: str,
                              all_user_roots: List[Tuple[str, str]]) -> bool:
    """
    Verify that a user's data is included in the aggregated root
    
    Args:
        user_address: Address of the user to verify
        user_root: User's individual Merkle root
        aggregated_root: The aggregated root to verify against
        all_user_roots: All user roots that were aggregated
        
    Returns:
        True if user is included in aggregation
    """
    
    # Find user's position
    sorted_roots = sorted(all_user_roots, key=lambda x: x[0])
    user_index = None
    
    for i, (addr, root) in enumerate(sorted_roots):
        if addr == user_address and root == user_root:
            user_index = i
            break
    
    if user_index is None:
        return False
    
    # Create the aggregation tree
    leaves = [f"{addr}:{root}" for addr, root in sorted_roots]
    agg_tree = MerkleTree(leaves)
    
    # Verify the aggregated root matches
    if agg_tree.root != aggregated_root:
        return False
    
    # Get and verify proof for the user
    element = f"{user_address}:{user_root}"
    proof = agg_tree.get_proof(user_index)
    
    return agg_tree.verify_proof(element, user_index, proof)