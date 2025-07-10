import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse

def crawl_posters_site(start_urls, base_url, max_pages=20):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })
    
    visited = set()
    to_visit = list(start_urls)
    results = []
    
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
            
        print(f"Crawling: {url}")
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
            
            # Look for poster-specific elements
            poster_elements = []
            
            # Search for result items (common in Primo interfaces)
            result_items = soup.find_all(['div'], class_=lambda x: x and ('result' in x.lower() or 'item' in x.lower()))
            for item in result_items[:3]:  # Just first few for analysis
                poster_elements.append({
                    'class': item.get('class'),
                    'text_snippet': item.get_text(strip=True)[:200]
                })
            
            # Look for search forms
            search_forms = soup.find_all('form')
            form_info = []
            for form in search_forms:
                form_info.append({
                    'action': form.get('action'),
                    'method': form.get('method'),
                    'inputs': [{'name': inp.get('name'), 'type': inp.get('type')} for inp in form.find_all('input')[:5]]
                })
            
            results.append({
                "url": url,
                "title": title,
                "headings": headings,
                "poster_elements": poster_elements,
                "search_forms": form_info,
                "page_type": "search_results" if "van%20gogh" in url else "main_page" if "search?" in url else "detail_page"
            })
            
            # Look for relevant links (but limit crawling scope)
            for a in soup.find_all('a', href=True):
                link = a['href']
                abs_link = urljoin(url, link)
                parsed = urlparse(abs_link)
                
                # Only follow links within the posters domain
                if parsed.netloc == "nb-posters.primo.exlibrisgroup.com":
                    if abs_link not in visited and abs_link not in to_visit:
                        # Limit to relevant pages
                        if any(x in abs_link for x in ['search', 'discovery', 'fulldisplay']):
                            to_visit.append(abs_link)
                            
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
            
        visited.add(url)
    
    # Save results
    output_dir = "../output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "posters_crawl_summary.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Posters crawl summary saved to {output_file}")
    return results

def main():
    start_urls = [
        "https://nb-posters.primo.exlibrisgroup.com/discovery/search?search_scope=MyInstitution&vid=41SNL_53_INST:posters&lang=en",
        "https://nb-posters.primo.exlibrisgroup.com/discovery/search?query=any,contains,van%20gogh&tab=LibraryCatalog&search_scope=MyInstitution&vid=41SNL_53_INST:posters&lang=en&offset=0",
        "https://nb-posters.primo.exlibrisgroup.com/discovery/fulldisplay?docid=alma991000324799703978&context=L&vid=41SNL_53_INST:posters&lang=en&search_scope=MyInstitution&adaptor=Local%20Search%20Engine&tab=LibraryCatalog&query=any,contains,van%20gogh&offset=0"
    ]
    
    base_url = "https://nb-posters.primo.exlibrisgroup.com"
    crawl_posters_site(start_urls, base_url, max_pages=10)

if __name__ == "__main__":
    main() 