import requests
import time
import json

def fetch_all_books(search_term="", max_results=8):
    books = []
    offset = 0
    limit = 8  # You can increase this if the API allows
    total = None
    while len(books) < max_results:
        params = {
            "acTriggered": "false",
            "blendFacetsSeparately": "false",
            "citationTrailFilterByAvailability": "true",
            "disableCache": "false",
            "getMore": "0",
            "inst": "41SNL_51_INST",
            "isCDSearch": "false",
            "lang": "en",
            "limit": limit,
            "newspapersActive": "false",
            "newspapersSearch": "false",
            "offset": offset,
            "otbRanking": "false",
            "pcAvailability": "true",
            "q": f"any,contains,{search_term}",
            "qExclude": "",
            "qInclude": "rtype,exact,books",
            "rapido": "false",
            "refEntryActive": "false",
            "rtaLinks": "true",
            "scope": "MyInstitution",
            "searchInFulltextUserSelection": "true",
            "search_scope": "MyInstitution",
            "skipDelivery": "Y",
            "sort": "rank",
            "tab": "LibraryCatalog",
            "vid": "41SNL_51_INST:helveticat"
        }
        url = "https://www.helveticat.ch/primaws/rest/pub/pnxs"
        headers = {
            "User-Agent": "ResearchBot/1.0 (contact: youremail@example.com)"
        }
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if total is None:
            total = data.get("info", {}).get("totalResultsLocal", 0)
            print(f"Total results: {total}")
        docs = data.get("docs", [])
        if not docs:
            break
        for book in docs:
            # Get the recordid for the details API
            recordid = book.get("pnx", {}).get("control", {}).get("recordid", [None])[0]
            if not recordid:
                continue
            details_url = f"https://www.helveticat.ch/primaws/rest/pub/pnxs/L/{recordid}"
            details_params = {
                "vid": "41SNL_51_INST:helveticat",
                "lang": "en",
                "search_scope": "MyInstitution",
                "adaptor": "Local Search Engine"
            }
            details_resp = requests.get(details_url, params=details_params, headers=headers)
            details_resp.raise_for_status()
            details_data = details_resp.json()
            # Extract only the necessary fields
            display = details_data.get("pnx", {}).get("display", {})
            delivery = details_data.get("delivery", {})
            filtered_book = {
                "title": display.get("title", []),
                "creator": display.get("creator", []),
                "subject": display.get("subject", []),
                "language": display.get("language", []),
                "format": display.get("format", []),
                "creationdate": display.get("creationdate", []),
                "publisher": display.get("publisher", []),
                "series": display.get("series", []),
                "genre": display.get("genre", []),
                "place": display.get("place", []),
                "mms": display.get("mms", []),
                "lds48": display.get("lds48", []),
                "mainLocation": delivery.get("bestlocation", {}).get("mainLocation", None),
                "callNumber": delivery.get("bestlocation", {}).get("callNumber", None),
                "availabilityStatus": delivery.get("bestlocation", {}).get("availabilityStatus", None),
                "thumbnail": None
            }
            # Get thumbnail if available
            links = delivery.get("link", [])
            for link in links:
                if link.get("linkType") == "thumbnail":
                    filtered_book["thumbnail"] = link.get("linkURL")
                    break
            books.append(filtered_book)
            if len(books) >= max_results:
                break
            time.sleep(1)  # Be polite between detail requests
        offset += limit
        print(f"Fetched {len(books)} / {total}")
        time.sleep(10)  # Be polite between pages
        if len(books) >= max_results:
            break
        if offset >= total:
            break
    return books

if __name__ == "__main__":
    search_term = "van gogh"
    results = fetch_all_books(search_term, max_results=8)
    # Save only the first 8 books
    results_to_save = results[:8]
    with open("sample_books8.json", "w", encoding="utf-8") as f:
        json.dump(results_to_save, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results_to_save)} samples to sample_books8.json")