"""
Base Provider - Abstract base class for all LLM providers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion for given prompt"""
        pass
    
    @abstractmethod
    def get_status(self) -> str:
        """Get provider status (ready, error, etc)"""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model being used"""
        return {
            "provider": self.__class__.__name__,
            "status": self.get_status()
        }