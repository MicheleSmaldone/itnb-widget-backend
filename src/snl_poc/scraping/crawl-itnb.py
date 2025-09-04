import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse
import time

def crawl_itnb_site(start_urls, base_url, max_pages=50):
    """
    Crawl ITNB website to discover all available pages
    """
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
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Extract basic page info
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4'])]
            
            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                meta_desc = meta_tag.get('content', '')
            
            # Extract main content areas
            main_content = []
            # Look for main content containers
            for container in soup.find_all(['main', 'article', 'section']):
                content_text = container.get_text(strip=True)
                if content_text and len(content_text) > 50:  # Only meaningful content
                    main_content.append(content_text[:500])  # Truncate for summary
            
            # Extract navigation structure
            nav_links = []
            for nav in soup.find_all(['nav', 'ul']):
                for link in nav.find_all('a', href=True):
                    link_text = link.get_text(strip=True)
                    if link_text:
                        nav_links.append({
                            'text': link_text,
                            'href': link['href']
                        })
            
            # Categorize page type based on URL and content
            page_type = categorize_page_type(url, soup)
            
            results.append({
                "url": url,
                "title": title,
                "meta_description": meta_desc,
                "headings": headings,
                "main_content_snippets": main_content[:3],  # First 3 content blocks
                "navigation_links": nav_links[:10],  # First 10 nav links
                "page_type": page_type,
                "content_length": len(soup.get_text(strip=True))
            })
            
            # Find new links to crawl
            for a in soup.find_all('a', href=True):
                link = a['href']
                abs_link = urljoin(url, link)
                parsed = urlparse(abs_link)
                
                # Only follow links within itnb.ch domain
                if parsed.netloc == urlparse(base_url).netloc:
                    if abs_link not in visited and abs_link not in to_visit:
                        # Filter out common non-content links
                        if not any(x in abs_link.lower() for x in ['#', 'javascript:', 'tel:', 'mailto:', '.pdf', '.jpg', '.png']):
                            # Prefer English pages
                            if "/en/" in abs_link or abs_link.endswith("/en"):
                                to_visit.append(abs_link)
                            elif "/en/" not in url:  # Add non-English only if current page isn't English
                                to_visit.append(abs_link)
            
            # Be polite to the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
            
        visited.add(url)
    
    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), "scrape_out")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "itnb_crawl_summary.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"ITNB crawl summary saved to {output_file}")
    print(f"Discovered {len(results)} pages")
    
    # Also save a simple URL list for easy reference
    url_list_file = os.path.join(output_dir, "itnb_urls.txt")
    with open(url_list_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(f"{result['page_type']}: {result['url']}\n")
    
    return results

def categorize_page_type(url, soup):
    """
    Categorize the page type based on URL patterns and content
    """
    url_lower = url.lower()
    
    # Check URL patterns first
    if url_lower.endswith('/en') or url_lower.endswith('/'):
        return "homepage"
    elif 'product' in url_lower or 'service' in url_lower:
        return "product_service"
    elif 'solution' in url_lower:
        return "solution"
    elif 'company' in url_lower or 'about' in url_lower:
        return "company"
    elif 'contact' in url_lower:
        return "contact"
    elif 'news' in url_lower or 'blog' in url_lower:
        return "news"
    elif 'partner' in url_lower or 'ecosystem' in url_lower:
        return "partner"
    elif 'career' in url_lower:
        return "career"
    
    # Check content patterns if URL doesn't give clear indication
    page_text = soup.get_text().lower()
    if 'sovereign cloud' in page_text and ('infrastructure' in page_text or 'service' in page_text):
        return "product_service"
    elif 'ai model' in page_text:
        return "product_service"
    elif 'cybersecurity' in page_text:
        return "product_service"
    elif 'professional services' in page_text:
        return "product_service"
    elif 'speedboat' in page_text:
        return "product_service"
    elif 'sovereign orchestrator' in page_text:
        return "product_service"
    
    return "general"

def main():
    base_url = "https://www.itnb.ch"
    start_urls = [
        f"{base_url}/en",  # English homepage
        f"{base_url}/en/products-and-services",
        f"{base_url}/en/solutions", 
        f"{base_url}/en/company"
    ]
    
    crawl_itnb_site(start_urls, base_url, max_pages=30)

if __name__ == "__main__":
    main()
