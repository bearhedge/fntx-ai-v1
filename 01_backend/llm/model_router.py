"""
Model Router - Central routing logic for LLM selection based on agent type and task
"""

import os
import logging
from typing import Dict, Any, Optional
from .providers.base import BaseProvider
from .providers.gemini import GeminiProvider
from .providers.local import LocalModelProvider

logger = logging.getLogger(__name__)

class ModelRouter:
    """Routes LLM requests to appropriate providers based on agent type and configuration"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.providers = self._initialize_providers()
        self.default_provider = os.getenv('DEFAULT_LLM_PROVIDER', 'gemini')
        
    def _initialize_providers(self) -> Dict[str, BaseProvider]:
        """Initialize available LLM providers"""
        providers = {}
        
        # Initialize Gemini provider if API key is available
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            providers['gemini'] = GeminiProvider(api_key=gemini_api_key)
            logger.info("Gemini provider initialized")
        else:
            logger.warning("GEMINI_API_KEY not found in environment")
        
        # Initialize local model provider if endpoint is configured
        local_endpoint = os.getenv('LOCAL_MODEL_ENDPOINT', 'http://localhost:8005')
        if local_endpoint:
            providers['local'] = LocalModelProvider(endpoint=local_endpoint)
            logger.info(f"Local model provider initialized at {local_endpoint}")
        
        return providers
    
    def get_provider(self, agent_type: str, task_type: Optional[str] = None) -> BaseProvider:
        """
        Get appropriate LLM provider based on agent type and task
        
        Routing logic:
        - strategic, orchestrator -> Gemini (cloud)
        - execution, evaluation -> Local (self-hosted) if available, else Gemini
        - environment, reward -> Local preferred for real-time tasks
        """
        # Override with environment variable if set
        forced_provider = os.getenv(f'{agent_type.upper()}_LLM_PROVIDER')
        if forced_provider and forced_provider in self.providers:
            return self.providers[forced_provider]
        
        # Strategic planning and orchestration use cloud LLM
        if agent_type in ['strategic', 'orchestrator', 'strategic-planner']:
            if 'gemini' in self.providers:
                return self.providers['gemini']
            else:
                raise ValueError("Gemini provider not available for strategic planning")
        
        # Execution and evaluation prefer local models for speed
        elif agent_type in ['execution', 'evaluation', 'executor', 'evaluator']:
            if 'local' in self.providers:
                return self.providers['local']
            elif 'gemini' in self.providers:
                logger.info(f"Local model not available, falling back to Gemini for {agent_type}")
                return self.providers['gemini']
        
        # Environment and reward models prefer local for real-time
        elif agent_type in ['environment', 'reward', 'environment-watcher', 'reward-model']:
            if 'local' in self.providers:
                return self.providers['local']
            elif 'gemini' in self.providers:
                return self.providers['gemini']
        
        # Default fallback
        if self.default_provider in self.providers:
            return self.providers[self.default_provider]
        
        # If no providers available
        raise ValueError(f"No LLM provider available for agent type: {agent_type}")
    
    def generate_completion(self, agent_type: str, prompt: str, **kwargs) -> str:
        """Generate completion using appropriate provider"""
        provider = self.get_provider(agent_type)
        return provider.generate(prompt, **kwargs)
    
    async def generate_completion_async(self, agent_type: str, prompt: str, **kwargs) -> str:
        """Async version of generate_completion"""
        provider = self.get_provider(agent_type)
        if hasattr(provider, 'generate_async'):
            return await provider.generate_async(prompt, **kwargs)
        else:
            # Fallback to sync version
            return provider.generate(prompt, **kwargs)
    
    def list_available_providers(self) -> Dict[str, str]:
        """List all available providers and their status"""
        return {
            name: provider.get_status() 
            for name, provider in self.providers.items()
        }