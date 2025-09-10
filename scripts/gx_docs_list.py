#!/usr/bin/env python
import os
from dotenv import load_dotenv
from groundx import GroundX


def ensure_env_defaults() -> None:
    if not os.getenv("GROUNDX_API_KEY"):
        os.environ["GROUNDX_API_KEY"] = "5c49be10-d228-4dd8-bbb0-d59300698ef6"
    if not os.getenv("GROUNDX_BASE_URL"):
        os.environ["GROUNDX_BASE_URL"] = "https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api"


def main() -> None:
    load_dotenv()
    ensure_env_defaults()

    api_key = os.environ["GROUNDX_API_KEY"]
    base_url = os.environ.get("GROUNDX_BASE_URL")
    gx = GroundX(api_key=api_key, base_url=base_url)

    bucket_id = int(os.getenv("GROUNDX_BUCKET_ID", "69"))
    print(f"Listing documents in bucket {bucket_id}")

    docs = gx.documents.lookup(id=bucket_id)
    found = False
    if hasattr(docs, "documents") and docs.documents:
        for d in docs.documents:
            name = getattr(d, "file_name", None)
            did = getattr(d, "document_id", None)
            print(f"- {name} (id={did})")
            if name == "company_about-itnb_extracted.json":
                found = True
    else:
        print("No documents found or unexpected response format.")

    if not found:
        print("company_about-itnb_extracted.json not found in bucket.")
    else:
        print("company_about-itnb_extracted.json is present.")


if __name__ == "__main__":
    main()


