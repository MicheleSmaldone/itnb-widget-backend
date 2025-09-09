#!/usr/bin/env python3

import os
import logging
from groundx import GroundX
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BucketInspector:
    """Inspect GroundX bucket contents and status"""
    
    def __init__(self, bucket_name: str = "itnb-website-widget"):
        """Initialize the bucket inspector"""
        self.bucket_name = bucket_name
        self.bucket_id = None
        
        # Initialize GroundX client with on-prem configuration
        api_key = os.getenv("GROUNDX_API_KEY", "5c49be10-d228-4dd8-bbb0-d59300698ef6")
        base_url = os.getenv("GROUNDX_BASE_URL", "https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api")
        
        self.client = GroundX(
            api_key=api_key,
            base_url=base_url
        )
        
        # Find the bucket with documents
        self._find_active_bucket()
    
    def _find_active_bucket(self) -> Optional[int]:
        """Find the bucket with the most documents"""
        try:
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
            self.bucket_id = active_bucket['id']
            
            logger.info(f"Selected bucket '{self.bucket_name}' (ID: {self.bucket_id}) with {active_bucket['doc_count']} documents")
            return self.bucket_id
            
        except Exception as e:
            logger.error(f"Error finding active bucket: {str(e)}")
            return None
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """Get detailed bucket information"""
        try:
            if not self.bucket_id:
                return {"error": "No active bucket found"}
            
            # Get documents in this bucket
            documents_response = self.client.documents.list()
            bucket_docs = []
            
            if hasattr(documents_response, 'documents') and documents_response.documents:
                bucket_docs = [doc for doc in documents_response.documents if doc.bucket_id == self.bucket_id]
            
            info = {
                "bucket_name": self.bucket_name,
                "bucket_id": self.bucket_id,
                "total_documents": len(bucket_docs),
                "documents": []
            }
            
            for doc in bucket_docs:
                doc_info = {
                    "file_name": doc.file_name,
                    "document_id": doc.document_id
                }
                info["documents"].append(doc_info)
            
            return info
            
        except Exception as e:
            return {"error": f"Failed to get bucket info: {str(e)}"}
    
    def print_bucket_status(self) -> None:
        """Print formatted bucket status"""
        info = self.get_bucket_info()
        
        if "error" in info:
            print(f"❌ {info['error']}")
            return
        
        print("=" * 60)
        print(f"📦 GROUNDX BUCKET STATUS")
        print("=" * 60)
        print(f"🗂️  Bucket Name: {info['bucket_name']}")
        print(f"🔢 Bucket ID: {info['bucket_id']}")
        print(f"📁 Total Documents: {info['total_documents']}")
        print("-" * 60)
        
        if info['documents']:
            print("📄 DOCUMENTS IN BUCKET:")
            for i, doc in enumerate(info['documents'], 1):
                print(f"   {i:2d}. {doc['file_name']}")
                print(f"       ID: {doc['document_id']}")
        else:
            print("   No documents found in bucket")
        
        print("=" * 60)

def inspect_itnb_bucket():
    """Main function to inspect the ITNB bucket"""
    inspector = BucketInspector("itnb-website-widget")
    inspector.print_bucket_status()
    return inspector

if __name__ == "__main__":
    inspect_itnb_bucket()
