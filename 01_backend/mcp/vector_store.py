"""
Vector store integration for semantic memory search in MCP system.
Uses Pinecone for efficient similarity search across agent memories.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np

from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector store wrapper for semantic search capabilities.
    """
    
    def __init__(self, api_key: str, environment: str, index_name: str):
        """
        Initialize vector store client.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment
            index_name: Name of the index to use
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self._client: Optional[Pinecone] = None
        self._index = None
        
    async def initialize(self) -> None:
        """Initialize Pinecone client and create/connect to index."""
        try:
            # Initialize Pinecone
            self._client = Pinecone(api_key=self.api_key)
            
            # Check if index exists
            existing_indexes = self._client.list_indexes()
            index_exists = any(idx.name == self.index_name for idx in existing_indexes)
            
            if not index_exists:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                
                # Create index with serverless spec
                self._client.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                
            # Connect to index
            self._index = self._client.Index(self.index_name)
            
            # Wait for index to be ready
            stats = self._index.describe_index_stats()
            logger.info(f"Connected to Pinecone index: {self.index_name} "
                       f"(vectors: {stats.total_vector_count})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
            
    async def close(self) -> None:
        """Close vector store connection."""
        # Pinecone doesn't require explicit closing
        logger.info("Vector store closed")
        
    async def upsert(self, vectors: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Insert or update vectors.
        
        Args:
            vectors: List of vector dictionaries with id, values, and metadata
            
        Returns:
            Dict with upsert statistics
        """
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            # Prepare vectors for upsert
            formatted_vectors = []
            for vec in vectors:
                formatted = {
                    'id': vec['id'],
                    'values': vec['values'],
                    'metadata': vec.get('metadata', {})
                }
                formatted_vectors.append(formatted)
                
            # Upsert in batches
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(formatted_vectors), batch_size):
                batch = formatted_vectors[i:i + batch_size]
                response = self._index.upsert(vectors=batch)
                total_upserted += response.upserted_count
                
            logger.info(f"Upserted {total_upserted} vectors to Pinecone")
            
            return {'upserted_count': total_upserted}
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise
            
    async def search(self, embedding: List[float], top_k: int = 10,
                    filter: Optional[Dict[str, Any]] = None,
                    include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of results to return
            filter: Metadata filter dictionary
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of search results with id, score, and metadata
        """
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            # Perform search
            results = self._index.query(
                vector=embedding,
                top_k=top_k,
                filter=filter,
                include_metadata=include_metadata
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                result = {
                    'id': match.id,
                    'score': match.score
                }
                if include_metadata and hasattr(match, 'metadata'):
                    result['metadata'] = match.metadata
                    
                formatted_results.append(result)
                
            logger.debug(f"Found {len(formatted_results)} similar vectors")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise
            
    async def fetch(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch vectors by ID.
        
        Args:
            ids: List of vector IDs to fetch
            
        Returns:
            Dict mapping IDs to vector data
        """
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            response = self._index.fetch(ids=ids)
            
            # Format response
            vectors = {}
            for id, data in response.vectors.items():
                vectors[id] = {
                    'values': data.values,
                    'metadata': data.metadata if hasattr(data, 'metadata') else {}
                }
                
            logger.debug(f"Fetched {len(vectors)} vectors")
            
            return vectors
            
        except Exception as e:
            logger.error(f"Failed to fetch vectors: {e}")
            raise
            
    async def delete(self, ids: List[str]) -> None:
        """
        Delete vectors by ID.
        
        Args:
            ids: List of vector IDs to delete
        """
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            self._index.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise
            
    async def delete_all(self) -> None:
        """Delete all vectors in the index."""
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            self._index.delete(delete_all=True)
            logger.info("Deleted all vectors from Pinecone index")
            
        except Exception as e:
            logger.error(f"Failed to delete all vectors: {e}")
            raise
            
    async def update_metadata(self, id: str, metadata: Dict[str, Any]) -> None:
        """
        Update vector metadata.
        
        Args:
            id: Vector ID
            metadata: New metadata dictionary
        """
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            # Fetch existing vector
            response = self._index.fetch(ids=[id])
            if id not in response.vectors:
                raise ValueError(f"Vector {id} not found")
                
            # Update with new metadata
            vector = response.vectors[id]
            self._index.upsert(vectors=[{
                'id': id,
                'values': vector.values,
                'metadata': metadata
            }])
            
            logger.debug(f"Updated metadata for vector {id}")
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            raise
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._index:
            raise RuntimeError("Vector store not initialized")
            
        try:
            stats = self._index.describe_index_stats()
            
            return {
                'total_vectors': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'namespaces': stats.namespaces
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise