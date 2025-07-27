"""
FNTX Blockchain Integration

Provides Python interface to interact with FNTX smart contracts on Polygon.
"""

from .integration import FNTXBlockchain
from .utils import (
    format_date,
    ipfs_upload,
    ipfs_retrieve,
    calculate_metrics
)

__all__ = [
    'FNTXBlockchain',
    'format_date',
    'ipfs_upload',
    'ipfs_retrieve',
    'calculate_metrics'
]