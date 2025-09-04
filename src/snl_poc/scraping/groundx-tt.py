from groundx import GroundX, Document
import urllib.request, json, time


# BUCKET_ID = 6
# GROUNDX_API_KEY = "5c49be10-d228-4dd8-bbb0-d59300698ef6"
# GROUNDX_BASE_URL = "https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api"

# authenticating
client = GroundX(
    api_key="5c49be10-d228-4dd8-bbb0-d59300698ef6",
    base_url="https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api"
)

# (1) creating a new bucket with all posters

# creating a new bucket
bucket_response = client.buckets.create(
  name="TEST444"
)

# storing the bucket_id
bucket_id = bucket_response.bucket.bucket_id


# (2) ingesting the documents

ingest_response = client.ingest(
    documents=[
        Document(
            bucket_id=bucket_id,
            file_name="about-itnb_certificates-and-compliance",
            file_path="/app/src/snl_poc/scraping/scrape_out/company_about-itnb_certificates-and-compliance_extracted.json",
            file_type="json"
        )
    ]
)

# (3) waiting for the documents to be ingested

while (True):
    ingest_response = client.documents.get_processing_status_by_id(
        process_id=ingest_response.ingest.process_id,
    )
    if (ingest_response.ingest.status == "complete" or ingest_response.ingest.status == "cancelled"):
        break
    if (ingest_response.ingest.status == "error"):
        raise ValueError('Error Ingesting Document')
    print(ingest_response.ingest.status)
    time.sleep(3)


# # (4) getting the parsed documents from the bucket
# # Getting parsed documents from the bucket
# document_response = client.documents.lookup(
#     id=bucket_id
# )

# # Getting the X-Ray parsing results for one of the documents
# xray_url = document_response.documents[0].xray_url
# with urllib.request.urlopen(xray_url) as url:
#     data = json.loads(url.read().decode())
#     print(data)
