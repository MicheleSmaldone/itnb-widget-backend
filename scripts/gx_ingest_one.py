#!/usr/bin/env python
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from groundx import GroundX, Document


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
    file_path = os.getenv(
        "GROUNDX_INGEST_FILE",
        "/app/src/snl_poc/scraping/scrape_out/company_about-itnb_extracted.json",
    )

    p = Path(file_path)
    if not p.exists():
        print(f"File not found: {file_path}")
        return

    doc = Document(
        bucket_id=bucket_id,
        file_name=p.name,
        file_path=str(p),
        file_type="json",
    )

    print(f"Ingesting {p.name} into bucket {bucket_id}...")
    resp = gx.ingest(documents=[doc])
    process_id = getattr(getattr(resp, "ingest", None), "process_id", None)
    print(f"process_id: {process_id}")

    # Wait briefly for processing
    if process_id:
        for _ in range(10):
            status_resp = gx.documents.get_processing_status_by_id(process_id=process_id)
            status = getattr(getattr(status_resp, "ingest", None), "status", None) or getattr(status_resp, "status", None)
            print(f"status: {status}")
            if status and str(status).lower() in {"complete", "failed", "cancelled", "error"}:
                break
            time.sleep(3)

    print("Done.")


if __name__ == "__main__":
    main()


