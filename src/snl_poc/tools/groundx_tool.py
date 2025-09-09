import os
import logging
import base64
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Type
from groundx import GroundX, Document
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GroundXSearchSchema(BaseModel):
    """Input schema for GroundX search."""
    query: str = Field(..., description="The search query to find relevant information")

class GroundXTool(BaseTool):
    """Tool for retrieving information from internal documents."""
    
    name: str = "GroundX RAG Search"
    description: str = """
    Use this tool when you need to search for specific information in company documents.
    Provide a clear and detailed query to find the most relevant information.
    """
    args_schema: Type[BaseModel] = GroundXSearchSchema
    bucket_name: str = "itnb"
    client: Optional[Any] = None
    _bucket_id: Optional[int] = None
    _knowledge_dir: Optional[str] = None
    _ingested_files: Dict[str, bool] = {}
    max_chunks: int = 4  # Configurable max chunks to retrieve
    
    def __init__(
        self,
        bucket_name: str = "itnb",
        bucket_id: Optional[int] = None,
        knowledge_dir: Optional[str] = None,
        max_chunks: int = 4,
        **kwargs
    ):
        """Initialize the GroundX tool."""
        super().__init__(**kwargs)
        
        # Initialize GroundX client with on-premise configuration
        api_key = os.getenv("GROUNDX_API_KEY")
        base_url = os.getenv("GROUNDX_BASE_URL")
        if not api_key:
            raise ValueError("GROUNDX_API_KEY not found in environment variables")
        
        # Use on-premise configuration if available
        if base_url:
            self.client = GroundX(api_key=api_key, base_url=base_url)
            logger.info(f"Using on-premise GroundX at: {base_url}")
        else:
            self.client = GroundX(api_key=api_key)
            logger.info("Using default GroundX API")
        self.bucket_name = bucket_name
        self.max_chunks = max_chunks
        
        # Set knowledge directory
        self._knowledge_dir = knowledge_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "knowledge"
        )
        logger.info(f"Knowledge directory: {self._knowledge_dir}")
        
        # Setup bucket and store ID
        if bucket_id:
            # Use directly provided bucket_id
            self._bucket_id = bucket_id
            logger.info(f"Using directly specified bucket ID: {bucket_id}")
        else:
            # Use bucket name lookup (existing behavior)
            self._bucket_id = self._setup_bucket_improved()
        
        # Get existing documents
        self._get_existing_documents()
        
        # Print bucket status for debugging
        self._print_bucket_status()
    
    def _setup_bucket_improved(self) -> Optional[int]:
        """Find the bucket with the most documents using improved logic."""
        try:
            logger.info(f"Setting up bucket '{self.bucket_name}' using improved discovery...")
            
            # List all buckets
            buckets_response = self.client.buckets.list()
            
            if not hasattr(buckets_response, 'buckets') or not buckets_response.buckets:
                logger.warning("No buckets found in the system")
                return None
            
            # Get all documents
            documents_response = self.client.documents.list()
            
            # Find buckets with matching name and count documents
            matching_buckets = []
            for bucket in buckets_response.buckets:
                if bucket.name == self.bucket_name:
                    doc_count = 0
                    if hasattr(documents_response, 'documents') and documents_response.documents:
                        doc_count = len([doc for doc in documents_response.documents if doc.bucket_id == bucket.bucket_id])
                    
                    matching_buckets.append({
                        'id': bucket.bucket_id,
                        'name': bucket.name,
                        'doc_count': doc_count
                    })
            
            if not matching_buckets:
                logger.warning(f"No buckets found with name '{self.bucket_name}'")
                return None
            
            # Use the bucket with the most documents
            active_bucket = max(matching_buckets, key=lambda b: b['doc_count'])
            
            logger.info(f"Selected bucket '{self.bucket_name}' (ID: {active_bucket['id']}) with {active_bucket['doc_count']} documents")
            return active_bucket['id']
            
        except Exception as e:
            logger.error(f"Error in improved bucket setup: {str(e)}")
            return None
    
    def _print_bucket_status(self) -> None:
        """Print bucket status information"""
        try:
            if not self._bucket_id:
                print("❌ No active bucket found")
                return
            
            # Get documents in this bucket
            documents_response = self.client.documents.list()
            bucket_docs = []
            
            if hasattr(documents_response, 'documents') and documents_response.documents:
                bucket_docs = [doc for doc in documents_response.documents if doc.bucket_id == self._bucket_id]
            
            print("=" * 50)
            print(f"📦 GroundX Bucket: {self.bucket_name} (ID: {self._bucket_id})")
            print(f"📁 Documents: {len(bucket_docs)}")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error getting bucket status: {str(e)}")
    
    def _setup_bucket(self) -> int:
        """Create a new bucket or get existing bucket ID."""
        try:
            logger.info(f"Setting up bucket '{self.bucket_name}'...")
            
            # List existing buckets
            buckets_response = self.client.buckets.list()
            
            # Check if bucket exists
            if hasattr(buckets_response, 'buckets'):
                for bucket in buckets_response.buckets:
                    if hasattr(bucket, 'bucket_id') and hasattr(bucket, 'name'):
                        if bucket.name == self.bucket_name:
                            logger.info(f"Found existing bucket '{self.bucket_name}' with ID {bucket.bucket_id}")
                            return bucket.bucket_id
            
            # Create new bucket
            create_response = self.client.buckets.create(name=self.bucket_name)
            
            # Get bucket ID from response
            if hasattr(create_response, 'bucket') and hasattr(create_response.bucket, 'bucket_id'):
                logger.info(f"Created new bucket '{self.bucket_name}' with ID {create_response.bucket.bucket_id}")
                return create_response.bucket.bucket_id
            
            raise ValueError(f"Could not extract bucket ID from response: {create_response}")
            
        except Exception as e:
            logger.error(f"Error setting up bucket: {str(e)}")
            raise
    
    def _get_existing_documents(self) -> None:
        """Get list of existing document names in the bucket to avoid duplicates."""
        try:
            logger.info(f"Retrieving existing documents for bucket {self._bucket_id}")
            docs = self.client.documents.lookup(id=self._bucket_id)
            
            if hasattr(docs, 'documents'):
                for doc in docs.documents:
                    if hasattr(doc, 'file_name'):
                        self._ingested_files[doc.file_name] = True
                        logger.info(f"Found existing document: {doc.file_name}")
            
            logger.info(f"Found {len(self._ingested_files)} existing documents")
        except Exception as e:
            logger.error(f"Error retrieving existing documents: {str(e)}")
            self._ingested_files = {}
    
    def ingest_documents(self) -> bool:
        """Ingest documents from the knowledge directory into the GroundX bucket."""
        try:
            # Verify knowledge directory exists
            knowledge_path = Path(self._knowledge_dir)
            if not knowledge_path.exists():
                logger.error(f"Knowledge directory not found: {self._knowledge_dir}")
                return False
            
            logger.info(f"Ingesting documents from {self._knowledge_dir} into bucket {self._bucket_id}")
            
            # Supported file types
            supported_extensions = {
                '.pdf': 'pdf',
                '.docx': 'docx', 
                '.xlsx': 'xlsx',
                '.pptx': 'pptx',
                '.txt': 'txt',
                '.csv': 'csv',
                '.doc': 'doc',
                '.xls': 'xls',
                '.ppt': 'ppt',
                '.md': 'md',
                '.json': 'json'
            }
            
            # Process files
            success = False
            new_docs = 0
            skipped_docs = 0
            
            for file_path in knowledge_path.glob("**/*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    try:
                        file_type = supported_extensions[file_path.suffix.lower()]
                        file_name = file_path.name
                        file_path_str = str(file_path.absolute())
                        
                        # Skip already ingested files
                        if file_name in self._ingested_files:
                            logger.info(f"Skipping already ingested file: {file_name}")
                            skipped_docs += 1
                            continue
                        
                        logger.info(f"Processing {file_name} ({file_type})")
                        
                        # Create document using the format from the documentation
                        doc = Document(
                            bucket_id=self._bucket_id,
                            file_name=file_name,
                            file_path=file_path_str,
                            file_type=file_type
                        )
                        
                        # Ingest document
                        logger.info(f"Ingesting document with bucket_id={self._bucket_id}, file_name={file_name}")
                        response = self.client.ingest(documents=[doc])
                        
                        # Get process_id directly as shown in logs
                        if hasattr(response, 'ingest') and hasattr(response.ingest, 'process_id'):
                            process_id = response.ingest.process_id
                            logger.info(f"Ingestion started for {file_name}. Process ID: {process_id}")
                            self._ingested_files[file_name] = True
                            new_docs += 1
                            success = True
                        else:
                            logger.error(f"Could not find process_id in response: {response}")
                    
                    except Exception as e:
                        logger.error(f"Error ingesting {file_path}: {str(e)}")
            
            # Consider it a success if we found documents, even if all were skipped
            total_docs = new_docs + skipped_docs
            if total_docs > 0 and not success:
                logger.info("No new documents were ingested, but existing documents were found and skipped")
                success = True
            elif total_docs == 0:
                logger.warning("No documents were found to process")

            logger.info(f"Ingestion summary: {new_docs} new files ingested, {skipped_docs} files skipped")
            return success
            
        except Exception as e:
            logger.error(f"Error ingesting documents: {str(e)}")
            return False
    
    def _wait_for_processing(self, process_id: str, max_attempts: int = 10) -> None:
        """Wait for document processing to complete."""
        import time
        
        logger.info(f"Waiting for processing to complete for process ID: {process_id}")
        attempts = 0
        while attempts < max_attempts:
            try:
                response = self.client.documents.get_processing_status_by_id(process_id=process_id)
                
                # Log the full response to understand its structure
                logger.info(f"Processing status response: {response}")
                
                # Check different possible status attributes
                status = None
                if hasattr(response, 'ingest'):
                    if hasattr(response.ingest, 'status'):
                        status = response.ingest.status
                elif hasattr(response, 'status'):
                    status = response.status
                
                if status:
                    logger.info(f"Processing status: {status}")
                    if status.lower() in ["complete", "failed", "cancelled", "error"]:
                        return
                
                attempts += 1
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error checking processing status: {str(e)}")
                attempts += 1
                time.sleep(5)
        
        logger.warning(f"Reached maximum wait attempts. Processing may still be ongoing.")
    
    def _run(self, query: str) -> str:
        try:
            print(f"[DEBUG GROUNDX] _run() called with query: '{query[:50]}...' (length: {len(query)})")
            
            # Validate query is not empty
            if not query or not query.strip():
                print(f"[DEBUG GROUNDX] Empty query detected, returning error message")
                return "Error: Search query cannot be empty. Please provide a valid search term."
            
            # Limit chunks at API level for efficiency
            print(f"[DEBUG GROUNDX] Requesting max {self.max_chunks} chunks from GroundX API")
            
            retrieval_start = time.time()
            search_result = self.client.search.content(
                id=self._bucket_id,
                query=query.strip(),  # Ensure query is trimmed
                verbosity=2,
                n=self.max_chunks  # Limit results at API level
            )
            retrieval_time = time.time() - retrieval_start
            print(f"[PROFILE] Retrieval took {retrieval_time:.2f} seconds")
            
            sources_set = set()
            texts = []
            total_chunks_found = 0
            
            if hasattr(search_result, 'search') and hasattr(search_result.search, 'results'):
                total_chunks_found = len(search_result.search.results)
                print(f"[DEBUG GROUNDX] Received {total_chunks_found} chunks from GroundX (requested max {self.max_chunks})")
                
                for i, result in enumerate(search_result.search.results):
                    text = getattr(result, 'text', '')
                    print(f"[DEBUG GROUNDX] Chunk {i+1} length: {len(text)} chars")
                    print(f"[DEBUG GROUNDX] Raw chunk {i+1}: {text[:200]}...")
                    try:
                        chunk_data = json.loads(text)
                        print(f"[DEBUG GROUNDX] Chunk {i+1} JSON keys: {list(chunk_data.keys())}")
                        # Extract source_url if it exists
                        if 'source_url' in chunk_data:
                            source_url = chunk_data['source_url']
                            sources_set.add(source_url)
                            print(f"[DEBUG GROUNDX] Found source_url in chunk {i+1}: {source_url}")
                        else:
                            print(f"[DEBUG GROUNDX] No source_url found in chunk {i+1}")
                        texts.append(text)
                    except json.JSONDecodeError:
                        print(f"[DEBUG GROUNDX] Chunk {i+1} is not valid JSON, using as plain text")
                        texts.append(text)
            else:
                print(f"[DEBUG GROUNDX] No search results found in response")
            
            print(f"[DEBUG GROUNDX] Using all {len(texts)} retrieved chunks (no post-retrieval limiting needed)")
            
            # Combine all text content
            content = "\n\n".join(texts)
            
            # Add sources in the format expected by frontend: [PRIMARY_SOURCE: url]
            if sources_set:
                sources_list = list(sources_set)
                # Frontend expects individual [PRIMARY_SOURCE: url] markers for each source
                primary_source_markers = []
                for url in sources_list:
                    primary_source_markers.append(f"[PRIMARY_SOURCE: {url}]")
                
                # Add all source markers to content
                sources_text = "\n\n" + "\n".join(primary_source_markers)
                content += sources_text
                
                print(f"[DEBUG GROUNDX] Added {len(sources_list)} source URLs in PRIMARY_SOURCE format")
                print(f"[DEBUG GROUNDX] Primary source markers: {sources_text.strip()}")
            
            print(f"[DEBUG GROUNDX] Final content length: {len(content)} chars")
            print(f"[DEBUG GROUNDX] Final content preview: {content[-200:]}")  # Last 200 chars to see sources
            return content
        
        except Exception as e:
            print(f"[DEBUG GROUNDX] Error in _run(): {str(e)}")
            return f"Error searching documents: {str(e)}"
    
    def test_search(self, query: str) -> str:
        """Test search functionality with the given query."""
        logger.info(f"Testing search with query: '{query}'")
        result = self._run(query)
        logger.info(f"Search result length: {len(result)}")
        return result
    
    def clear_bucket(self) -> bool:
        """Delete all documents in the bucket."""
        try:
            logger.info(f"Clearing all documents from bucket {self._bucket_id}")
            docs = self.client.documents.lookup(id=self._bucket_id)
            
            if hasattr(docs, 'documents'):
                doc_ids = []
                for doc in docs.documents:
                    if hasattr(doc, 'document_id'):
                        doc_ids.append(doc.document_id)
                
                if doc_ids:
                    logger.info(f"Deleting {len(doc_ids)} documents")
                    self.client.documents.delete(document_ids=doc_ids)
                    self._ingested_files = {}
                    return True
            
            logger.info("No documents to delete")
            return True
        except Exception as e:
            logger.error(f"Error clearing bucket: {str(e)}")
            return False


# Run document ingestion or test search if script is executed directly
if __name__ == "__main__":
    try:
        import sys
        tool = GroundXTool()
        
        # Handle clear flag
        if len(sys.argv) > 1 and sys.argv[1] == "--clear":
            logger.info("Clearing all documents from bucket...")
            success = tool.clear_bucket()
            if success:
                logger.info("Bucket cleared successfully")
            else:
                logger.error("Failed to clear bucket")
        # If a query argument is provided, test search
        elif len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
            logger.info(f"Testing search with query: {query}")
            result = tool.test_search(query)
            # print("\n--- SEARCH RESULTS ---\n")
            # print(result)
            # print("\n----------------------\n")
        # Otherwise try ingestion
        else:
            logger.info("No search query provided. Starting document ingestion...")
            success = tool.ingest_documents()
            if success:
                logger.info("Documents ingested successfully")
            else:
                logger.error("Failed to ingest documents")
                
    except Exception as e:
        logger.error(f"Error: {str(e)}") 