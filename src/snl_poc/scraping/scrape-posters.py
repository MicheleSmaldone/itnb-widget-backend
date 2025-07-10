import requests
import time
import json
import os

def fetch_van_gogh_posters(max_results=4):
    """
    Fetch Van Gogh posters from Swiss National Library posters collection
    """
    posters = []
    offset = 0
    limit = 8
    total = None
    
    base_api_url = "https://nb-posters.primo.exlibrisgroup.com/primaws/rest/pub/pnxs"
    
    while len(posters) < max_results:
        # API parameters for poster search
        params = {
            "acTriggered": "false",
            "blendFacetsSeparately": "false", 
            "citationTrailFilterByAvailability": "true",
            "disableCache": "false",
            "getMore": "0",
            "inst": "41SNL_53_INST",
            "isCDSearch": "false",
            "lang": "en",
            "limit": limit,
            "newspapersActive": "false",
            "newspapersSearch": "false", 
            "offset": offset,
            "otbRanking": "false",
            "pcAvailability": "true",
            "q": "any,contains,van gogh",
            "qExclude": "",
            "qInclude": "",  # No restriction like "rtype,exact,books"
            "rapido": "false",
            "refEntryActive": "false",
            "rtaLinks": "true",
            "scope": "MyInstitution",
            "searchInFulltextUserSelection": "true",
            "search_scope": "MyInstitution",
            "skipDelivery": "Y",
            "sort": "rank",
            "tab": "LibraryCatalog",
            "vid": "41SNL_53_INST:posters"  # Key difference - posters vid
        }
        
        headers = {
            "User-Agent": "ResearchBot/1.0 (Swiss National Library Research)",
            "Accept": "application/json",
            "Referer": "https://nb-posters.primo.exlibrisgroup.com/"
        }
        
        print(f"Fetching posters batch (offset: {offset})...")
        
        try:
            resp = requests.get(base_api_url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if total is None:
                total = data.get("info", {}).get("totalResultsLocal", 0)
                print(f"Total Van Gogh posters found: {total}")
            
            docs = data.get("docs", [])
            if not docs:
                print("No more results found")
                break
                
            for doc in docs:
                if len(posters) >= max_results:
                    break
                    
                # Extract poster information
                pnx = doc.get("pnx", {})
                display = pnx.get("display", {})
                control = pnx.get("control", {})
                
                recordid = control.get("recordid", [None])[0]
                if not recordid:
                    continue
                
                # Get detailed information
                try:
                    details_url = f"https://nb-posters.primo.exlibrisgroup.com/primaws/rest/pub/pnxs/L/{recordid}"
                    details_params = {
                        "vid": "41SNL_53_INST:posters",
                        "lang": "en", 
                        "search_scope": "MyInstitution",
                        "adaptor": "Local Search Engine"
                    }
                    
                    details_resp = requests.get(details_url, params=details_params, headers=headers, timeout=10)
                    details_resp.raise_for_status()
                    details_data = details_resp.json()
                    
                    # Extract poster details
                    poster_display = details_data.get("pnx", {}).get("display", {})
                    poster_delivery = details_data.get("delivery", {})
                    
                    poster_info = {
                        "recordid": recordid,
                        "title": poster_display.get("title", []),
                        "creator": poster_display.get("creator", []),
                        "subject": poster_display.get("subject", []),
                        "description": poster_display.get("description", []),
                        "language": poster_display.get("language", []),
                        "format": poster_display.get("format", []),
                        "type": poster_display.get("type", []),
                        "creationdate": poster_display.get("creationdate", []),
                        "publisher": poster_display.get("publisher", []),
                        "place": poster_display.get("place", []),
                        "relation": poster_display.get("relation", []),
                        "identifier": poster_display.get("identifier", []),
                        "source": poster_display.get("source", []),
                        "mms": poster_display.get("mms", []),
                        "thumbnail": None,
                        "availability": poster_delivery.get("bestlocation", {}).get("availabilityStatus", None),
                        "location": poster_delivery.get("bestlocation", {}).get("mainLocation", None),
                        "detail_url": f"https://nb-posters.primo.exlibrisgroup.com/discovery/fulldisplay?docid={recordid}&context=L&vid=41SNL_53_INST:posters&lang=en"
                    }
                    
                    # Get thumbnail if available
                    links = poster_delivery.get("link", [])
                    for link in links:
                        if link.get("linkType") == "thumbnail":
                            poster_info["thumbnail"] = link.get("linkURL")
                            break
                    
                    posters.append(poster_info)
                    print(f"Found poster: {poster_info['title'][:1][0] if poster_info['title'] else 'Unknown Title'}")
                    
                    time.sleep(1)  # Be polite between requests
                    
                except Exception as e:
                    print(f"Error fetching details for {recordid}: {e}")
                    continue
            
            offset += limit
            print(f"Fetched {len(posters)} / {max_results} posters")
            
            if len(posters) >= max_results:
                break
                
            time.sleep(2)  # Be polite between pages
            
        except Exception as e:
            print(f"Error fetching posters: {e}")
            break
    
    return posters

def main():
    print("Starting Van Gogh posters scraping...")
    
    # Fetch 4 Van Gogh posters
    van_gogh_posters = fetch_van_gogh_posters(max_results=4)
    
    # Save results
    output_dir = "../output"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "van_gogh_posters.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(van_gogh_posters, f, ensure_ascii=False, indent=2)
    
    print(f"\nSuccessfully scraped {len(van_gogh_posters)} Van Gogh posters")
    print(f"Results saved to: {output_file}")
    
    # Print summary
    print("\n=== POSTER SUMMARY ===")
    for i, poster in enumerate(van_gogh_posters, 1):
        title = poster['title'][0] if poster['title'] else "Unknown Title"
        creator = poster['creator'][0] if poster['creator'] else "Unknown Creator"
        date = poster['creationdate'][0] if poster['creationdate'] else "Unknown Date"
        print(f"{i}. {title}")
        print(f"   Creator: {creator}")
        print(f"   Date: {date}")
        print(f"   URL: {poster['detail_url']}")
        print()

if __name__ == "__main__":
    main() 