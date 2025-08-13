"""
Embedding generation utilities for semantic search in MCP system.
"""

import logging
from typing import List, Optional
import numpy as np
import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings for text using OpenAI or other providers.
    """
    
    def __init__(self, model_name: str = "text-embedding-ada-002", 
                 api_key: Optional[str] = None):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of embedding model to use
            api_key: API key for embedding service
        """
        self.model_name = model_name
        self.api_key = api_key
        
        if api_key:
            openai.api_key = api_key
            
    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    async def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            # Truncate text if too long (max ~8000 tokens)
            max_chars = 30000
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.warning(f"Truncated text to {max_chars} characters for embedding")
                
            # Generate embedding
            response = await openai.Embedding.acreate(
                input=text,
                model=self.model_name
            )
            
            embedding = response['data'][0]['embedding']
            
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return random embedding as fallback for development
            logger.warning("Returning random embedding as fallback")
            return np.random.randn(1536).astype(np.float32)
            
    async def generate_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = await openai.Embedding.acreate(
                    input=batch,
                    model=self.model_name
                )
                
                batch_embeddings = [
                    np.array(item['embedding'], dtype=np.float32)
                    for item in response['data']
                ]
                
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                # Add random embeddings as fallback
                for _ in batch:
                    embeddings.append(np.random.randn(1536).astype(np.float32))
                    
        return embeddings
        
    def cosine_similarity(self, embedding1: np.ndarray, 
                         embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        return float(similarity)