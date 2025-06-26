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
    client: Any = None
    _bucket_id: int = None
    _knowledge_dir: str = None
    _ingested_files: Dict[str, bool] = {}
    
    def __init__(
        self,
        bucket_name: str = "itnb",
        knowledge_dir: str = None,
        **kwargs
    ):
        """Initialize the GroundX tool."""
        super().__init__(**kwargs)
        
        # Initialize GroundX client
        api_key = os.getenv("GROUNDX_API_KEY")
        if not api_key:
            raise ValueError("GROUNDX_API_KEY not found in environment variables")
        
        self.client = GroundX(api_key=api_key)
        self.bucket_name = bucket_name
        
        # Set knowledge directory
        self._knowledge_dir = knowledge_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "knowledge"
        )
        logger.info(f"Knowledge directory: {self._knowledge_dir}")
        
        # Setup bucket and store ID
        self._bucket_id = self._setup_bucket()
        
        # Get existing documents
        self._get_existing_documents()
    
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
                '.md': 'md'
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
        """Run GroundX search with provided query."""
        try:
            if not query or not query.strip():
                return "Please provide a search query."
            
            logger.info(f"Searching for: {query}")
            
            # Execute search
            search_result = self.client.search.content(
                id=self._bucket_id,
                query=query,
                verbosity=2  # Include detailed results
            )
            
            # Log the search result structure only in debug mode
            if logger.level <= logging.DEBUG:
                logger.debug(f"Search result structure: {search_result}")
            
            # Return search.text as specified in the documentation
            if hasattr(search_result, 'search') and hasattr(search_result.search, 'text'):
                return search_result.search.text
            
            # Fallback to individual results
            results = []
            if hasattr(search_result, 'search') and hasattr(search_result.search, 'results'):
                for result in search_result.search.results:
                    if hasattr(result, 'text'):
                        results.append(result.text)
            
            if results:
                return "\n\n".join(results)
            
            return "No relevant information found."
        
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
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
            print("\n--- SEARCH RESULTS ---\n")
            print(result)
            print("\n----------------------\n")
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