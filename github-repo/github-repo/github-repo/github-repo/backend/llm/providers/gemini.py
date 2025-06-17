"""
Gemini Provider - Google Gemini API integration
"""

import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from .base import BaseProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseProvider):
    """Provider for Google Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = 'gemini-1.5-flash'):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name
        self.model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Gemini client"""
        if not self.api_key:
            logger.error("No Gemini API key provided")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini provider initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")
            self.model = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion using Gemini"""
        if not self.model:
            raise RuntimeError("Gemini provider not initialized")
        
        try:
            # Extract generation config from kwargs
            generation_config = kwargs.get('generation_config', {})
            if 'max_tokens' in kwargs:
                generation_config['max_output_tokens'] = kwargs['max_tokens']
            if 'temperature' in kwargs:
                generation_config['temperature'] = kwargs['temperature']
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(**generation_config) if generation_config else None
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async generation (Gemini SDK doesn't have native async, so we use sync)"""
        return self.generate(prompt, **kwargs)
    
    def get_status(self) -> str:
        """Get provider status"""
        if self.model:
            return "ready"
        elif not self.api_key:
            return "error: no API key"
        else:
            return "error: initialization failed"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = super().get_model_info()
        info.update({
            "model": self.model_name,
            "provider": "Google Gemini",
            "api_key_configured": bool(self.api_key)
        })
        return info