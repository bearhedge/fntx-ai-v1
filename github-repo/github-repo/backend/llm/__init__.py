"""
FNTX.ai LLM Module - Unified interface for all language model interactions
"""

from .model_router import ModelRouter
from .providers.gemini import GeminiProvider

__all__ = ['ModelRouter', 'GeminiProvider']