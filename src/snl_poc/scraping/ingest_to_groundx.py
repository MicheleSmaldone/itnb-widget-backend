import sys
import os
sys.path.append('/app/src/snl_poc/tools')

from groundx_tool import GroundXTool
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_phoenix_knowledge():
    """Ingest JSON files from knowledge directory to existing GroundX bucket"""
    
    # Create a custom GroundXTool that uses the existing bucket
    class PhoenixGroundXTool(GroundXTool):
        def __init__(self, **kwargs):
            # Initialize without calling _setup_bucket
            super(GroundXTool, self).__init__(**kwargs)
            
            # Initialize GroundX client
            api_key = os.getenv("GROUNDX_API_KEY")
            if not api_key:
                raise ValueError("GROUNDX_API_KEY not found in environment variables")
            
            from groundx import GroundX
            self.client = GroundX(api_key=api_key)
            self.bucket_name = "phoenix"
            self.max_chunks = 4
            
            # Set knowledge directory to the correct path
            self._knowledge_dir = "/app/src/snl_poc/knowledge"
            logger.info(f"Knowledge directory: {self._knowledge_dir}")
            
            # Use the existing bucket ID directly
            self._bucket_id = 20768
            logger.info(f"Using existing bucket ID: {self._bucket_id}")
            
            # Get existing documents
            self._get_existing_documents()
    
    try:
        # Create the tool instance
        tool = PhoenixGroundXTool()
        
        # Ingest documents
        logger.info("Starting document ingestion to GroundX bucket 20768...")
        success = tool.ingest_documents()
        
        if success:
            logger.info("✅ Documents ingested successfully!")
        else:
            logger.error("❌ Failed to ingest documents")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        return False

if __name__ == "__main__":
    success = ingest_phoenix_knowledge()
    if success:
        print("\n🎉 Ingestion completed successfully!")
    else:
        print("\n💥 Ingestion failed!")
        sys.exit(1)
