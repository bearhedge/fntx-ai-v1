"""
Local Model Provider - Integration with self-hosted models (e.g., DeepSeek)
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from .base import BaseProvider

logger = logging.getLogger(__name__)

class LocalModelProvider(BaseProvider):
    """Provider for local/self-hosted models"""
    
    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or os.getenv('LOCAL_MODEL_ENDPOINT', 'http://localhost:8005')
        self.timeout = int(os.getenv('LOCAL_MODEL_TIMEOUT', '30'))
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to local model endpoint"""
        try:
            response = requests.get(f"{self.endpoint}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"Local model provider connected to {self.endpoint}")
                self.connected = True
            else:
                logger.warning(f"Local model endpoint returned status {response.status_code}")
                self.connected = False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to local model endpoint: {e}")
            self.connected = False
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion using local model"""
        if not self.connected:
            raise RuntimeError("Local model provider not connected")
        
        try:
            # Prepare request payload
            payload = {
                "prompt": prompt,
                "max_tokens": kwargs.get('max_tokens', 500),
                "temperature": kwargs.get('temperature', 0.7),
                "top_p": kwargs.get('top_p', 0.9),
                "stream": False
            }
            
            # Make request to local model
            response = requests.post(
                f"{self.endpoint}/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('text', '').strip()
            else:
                raise RuntimeError(f"Local model returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Local model generation error: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async generation using aiohttp"""
        # For now, fallback to sync version
        # TODO: Implement proper async with aiohttp
        return self.generate(prompt, **kwargs)
    
    def get_status(self) -> str:
        """Get provider status"""
        if self.connected:
            return "ready"
        else:
            return f"error: cannot connect to {self.endpoint}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = super().get_model_info()
        info.update({
            "provider": "Local Model",
            "endpoint": self.endpoint,
            "connected": self.connected
        })
        return info