import os
import logging
import json
import time
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Type
from groundx import GroundX, Document
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GroundXSearchSchema(BaseModel):
    """Input schema for GroundX search."""
    query: str = Field(..., description="The search query to find relevant information")

class OptimizedGroundXTool(BaseTool):
    """Optimized GroundX tool with caching and error handling."""
    
    name: str = "GroundX RAG Search"
    description: str = "Search Phoenix Technologies documents for relevant information."
    args_schema: Type[BaseModel] = GroundXSearchSchema
    bucket_name: str = "phoenix"
    client: Optional[Any] = None
    _bucket_id: Optional[int] = None
    max_chunks: int = 3  # Reduced for faster responses
    _cache: Dict[str, str] = {}  # Response cache
    _cache_ttl: int = 3600  # 1 hour cache TTL
    _cache_timestamps: Dict[str, float] = {}
    
    def __init__(
        self,
        bucket_name: str = "phoenix",
        max_chunks: int = 3,
        **kwargs
    ):
        """Initialize the optimized GroundX tool."""
        super().__init__(**kwargs)
        
        # Initialize GroundX client
        api_key = os.getenv("GROUNDX_API_KEY")
        if not api_key:
            raise ValueError("GROUNDX_API_KEY not found in environment variables")
        
        self.client = GroundX(api_key=api_key)
        self.bucket_name = bucket_name
        self.max_chunks = max_chunks
        self._cache = {}
        self._cache_timestamps = {}
        
        # Get bucket ID (assume it exists - Phoenix bucket 20768)
        self._bucket_id = 20768  # Direct assignment for speed
        logger.info(f"Using bucket ID: {self._bucket_id}")
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[cache_key]) < self._cache_ttl
    
    def _run(self, query: str) -> str:
        start_time = time.time()
        
        try:
            # Input validation
            if not query or not query.strip():
                return "Error: Empty search query."
            
            # Check cache first
            cache_key = self._get_cache_key(query)
            if cache_key in self._cache and self._is_cache_valid(cache_key):
                print(f"[CACHE HIT] Returning cached result for: {query[:50]}...")
                print(f"[PROFILE] Cache retrieval took {time.time() - start_time:.2f} seconds")
                return self._cache[cache_key]
            
            print(f"[DEBUG GROUNDX] Searching for: '{query[:50]}...' (max {self.max_chunks} chunks)")
            
            # Search with error handling
            search_result = self.client.search.content(
                id=self._bucket_id,
                query=query.strip(),
                verbosity=2,
                n=self.max_chunks
            )
            
            # Process results safely
            texts = []
            sources_set = set()
            
            if (hasattr(search_result, 'search') and 
                hasattr(search_result.search, 'results') and 
                search_result.search.results is not None):
                
                for result in search_result.search.results:
                    if hasattr(result, 'text') and result.text:
                        try:
                            chunk_data = json.loads(result.text)
                            if isinstance(chunk_data, dict) and 'source_url' in chunk_data:
                                sources_set.add(chunk_data['source_url'])
                            texts.append(result.text)
                        except (json.JSONDecodeError, TypeError):
                            texts.append(result.text)
            
            # Build response
            content = "\n\n".join(texts) if texts else ""
            
            # Add source markers
            if sources_set:
                source_markers = [f"[PRIMARY_SOURCE: {url}]" for url in sources_set]
                content += "\n\n" + "\n".join(source_markers)
            
            # Handle no results
            if not content.strip():
                content = "No relevant information found in Phoenix Technologies documents."
            
            # Cache result
            self._cache[cache_key] = content
            self._cache_timestamps[cache_key] = time.time()
            
            print(f"[PROFILE] Total retrieval took {time.time() - start_time:.2f} seconds")
            print(f"[DEBUG GROUNDX] Found {len(texts)} chunks, {len(sources_set)} sources")
            
            return content
            
        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
    
    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        print("Cache cleared")
