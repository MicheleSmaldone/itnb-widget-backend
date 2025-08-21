import json
import os
from typing import Dict, List, Any

class PhoenixDataOptimizer:
    """
    Optimize Phoenix Technologies scraped data for LLM consumption
    """
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.load_data()
    
    def load_data(self):
        """Load the scraped data"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)
        self.pages = self.raw_data.get('pages', [])
    
    def optimize_for_qa(self) -> Dict[str, Any]:
        """
        Create an optimized structure for question-answering
        """
        optimized = {
            "company_overview": self.extract_company_overview(),
            "products_services": self.extract_products_services(),
            "solutions": self.extract_solutions(),
            "partnership_ecosystem": self.extract_partnerships(),
            "company_details": self.extract_company_details(),
            "contact_information": self.extract_contact_info(),
            "key_differentiators": self.extract_key_differentiators(),
            "search_index": self.create_search_index()
        }
        return optimized
    
    def extract_company_overview(self) -> Dict[str, Any]:
        """Extract high-level company information"""
        homepage = self.find_page_by_type("homepage")
        if not homepage:
            return {}
        
        return {
            "company_name": "Phoenix Technologies AG",
            "tagline": "We Make AI Work for You",
            "mission": homepage.get('meta_description', ''),
            "value_proposition": self.extract_value_prop(homepage),
            "headquarters": "Switzerland",
            "focus_areas": ["AI", "Cloud Infrastructure", "Cybersecurity", "Data Sovereignty"]
        }
    
    def extract_products_services(self) -> Dict[str, List[Dict]]:
        """Extract all products and services with details"""
        products = {
            "infrastructure_as_service": [],
            "platform_as_service": [],
            "software_as_service": [],
            "professional_services": [],
            "cybersecurity": []
        }
        
        product_pages = [p for p in self.pages if p.get('page_type') == 'product_service']
        
        for page in product_pages:
            product_info = {
                "name": self.extract_product_name(page),
                "category": self.categorize_product(page['url']),
                "description": page.get('meta_description', ''),
                "key_features": page.get('features', []),
                "benefits": page.get('benefits', []),
                "use_cases": page.get('use_cases', []),
                "technical_specs": page.get('technical_specs', []),
                "url": page['url']
            }
            
            category = self.categorize_product(page['url'])
            if category in products:
                products[category].append(product_info)
        
        return products
    
    def extract_solutions(self) -> Dict[str, List[Dict]]:
        """Extract industry solutions and use cases"""
        solutions = {
            "by_industry": [],
            "by_use_case": []
        }
        
        solution_pages = [p for p in self.pages if p.get('page_type') == 'solution']
        
        for page in solution_pages:
            solution_info = {
                "name": page.get('title', '').replace(' | Phoenix Technologies', ''),
                "description": page.get('meta_description', ''),
                "challenges_addressed": page.get('challenges_addressed', []),
                "solution_approach": page.get('solution_approach', ''),
                "outcomes": page.get('outcomes', []),
                "url": page['url']
            }
            
            if '/industries/' in page['url']:
                solution_info['industry'] = page.get('industry', '')
                solutions['by_industry'].append(solution_info)
            elif '/use-cases/' in page['url']:
                solution_info['use_case'] = page.get('use_case', '')
                solutions['by_use_case'].append(solution_info)
        
        return solutions
    
    def extract_partnerships(self) -> Dict[str, Any]:
        """Extract partnership and ecosystem information"""
        partner_pages = [p for p in self.pages if p.get('page_type') == 'partner']
        
        partnerships = {
            "partner_types": [],
            "key_partners": [],
            "success_stories": [],
            "innovation_centers": []
        }
        
        for page in partner_pages:
            partnerships['partner_types'].extend(page.get('partner_types', []))
            partnerships['key_partners'].extend(page.get('partner_list', []))
            partnerships['success_stories'].extend(page.get('success_stories', []))
        
        return partnerships
    
    def extract_company_details(self) -> Dict[str, Any]:
        """Extract detailed company information"""
        company_pages = [p for p in self.pages if p.get('page_type') == 'company']
        
        details = {
            "about": "",
            "team": [],
            "certifications": [],
            "career_opportunities": [],
            "compliance": []
        }
        
        for page in company_pages:
            if '/about' in page['url']:
                details['about'] = page.get('company_description', '')
            elif '/team' in page['url']:
                details['team'].extend(page.get('team_info', []))
            elif '/certificates' in page['url'] or '/compliance' in page['url']:
                details['certifications'].extend(page.get('certifications', []))
            elif '/career' in page['url']:
                details['career_opportunities'] = self.extract_career_info(page)
        
        return details
    
    def extract_contact_info(self) -> Dict[str, Any]:
        """Extract all contact information"""
        contact_info = {
            "general": {},
            "sales": {},
            "support": {},
            "locations": []
        }
        
        # Look for contact information across all pages
        for page in self.pages:
            page_contact = page.get('contact_info', {})
            if page_contact:
                if '/contact' in page.get('url', ''):
                    contact_info['general'].update(page_contact)
                else:
                    # Merge contact info from other pages
                    for key, value in page_contact.items():
                        if key not in contact_info['general'] and value:
                            contact_info['general'][key] = value
        
        return contact_info
    
    def extract_key_differentiators(self) -> List[str]:
        """Extract key differentiators and unique selling points"""
        differentiators = []
        
        # Common themes from Phoenix Technologies
        swiss_keywords = ['swiss', 'sovereignty', 'sovereign', 'compliance']
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning']
        security_keywords = ['security', 'secure', 'cybersecurity', 'protection']
        cloud_keywords = ['cloud', 'infrastructure', 'scalable']
        
        # Extract from homepage and key pages
        homepage = self.find_page_by_type("homepage")
        if homepage:
            content = homepage.get('main_content', '').lower()
            
            if any(word in content for word in swiss_keywords):
                differentiators.append("Swiss data sovereignty and compliance")
            if any(word in content for word in ai_keywords):
                differentiators.append("Specialized AI and ML infrastructure")
            if any(word in content for word in security_keywords):
                differentiators.append("Enterprise-grade security and cybersecurity services")
            if any(word in content for word in cloud_keywords):
                differentiators.append("Scalable cloud infrastructure solutions")
        
        # Add more specific differentiators
        differentiators.extend([
            "Swiss-certified confidential computing",
            "High-automation AI and Cloud Clusters",
            "Sovereign cloud infrastructure",
            "AI Model as a Service offerings",
            "Professional AI strategy consulting"
        ])
        
        return list(set(differentiators))  # Remove duplicates
    
    def create_search_index(self) -> List[Dict[str, Any]]:
        """Create a searchable index of all content"""
        search_index = []
        
        for page in self.pages:
            # Create searchable chunks
            index_entry = {
                "page_title": page.get('title', ''),
                "page_type": page.get('page_type', ''),
                "url": page['url'],
                "keywords": self.extract_keywords(page),
                "summary": page.get('meta_description', ''),
                "headings": [h.get('text', '') for h in page.get('headings', [])],
                "content_snippet": self.create_content_snippet(page)
            }
            search_index.append(index_entry)
        
        return search_index
    
    def extract_keywords(self, page: Dict) -> List[str]:
        """Extract relevant keywords from a page"""
        keywords = []
        
        # Extract from title
        title = page.get('title', '').lower()
        keywords.extend(title.split())
        
        # Extract from headings
        for heading in page.get('headings', []):
            keywords.extend(heading.get('text', '').lower().split())
        
        # Extract from meta description
        meta_desc = page.get('meta_description', '').lower()
        keywords.extend(meta_desc.split())
        
        # Clean and filter keywords
        keywords = [kw.strip('.,!?()[]{}";:') for kw in keywords if len(kw) > 2]
        
        return list(set(keywords))  # Remove duplicates
    
    def create_content_snippet(self, page: Dict) -> str:
        """Create a concise content snippet for search"""
        main_content = page.get('main_content', '')
        if main_content:
            # Take first 300 characters
            snippet = main_content[:300].strip()
            if len(main_content) > 300:
                snippet += "..."
            return snippet
        
        # Fallback to meta description
        return page.get('meta_description', '')
    
    def find_page_by_type(self, page_type: str) -> Dict:
        """Find the first page of a specific type"""
        for page in self.pages:
            if page.get('page_type') == page_type:
                return page
        return {}
    
    def extract_product_name(self, page: Dict) -> str:
        """Extract clean product name from page"""
        title = page.get('title', '')
        # Remove " | Phoenix Technologies" suffix
        return title.replace(' | Phoenix Technologies', '').strip()
    
    def categorize_product(self, url: str) -> str:
        """Categorize product based on URL structure"""
        url_lower = url.lower()
        
        if 'infrastructure-as-a-service' in url_lower:
            return 'infrastructure_as_service'
        elif 'platform-as-a-service' in url_lower:
            return 'platform_as_service'
        elif 'software-as-a-service' in url_lower:
            return 'software_as_service'
        elif 'professional-services' in url_lower:
            return 'professional_services'
        elif 'cybersecurity' in url_lower:
            return 'cybersecurity'
        else:
            return 'general'
    
    def extract_value_prop(self, homepage: Dict) -> str:
        """Extract value proposition from homepage"""
        main_content = homepage.get('main_content', '')
        
        # Look for the first substantial paragraph
        sentences = main_content.split('.')
        for sentence in sentences[:3]:  # Check first 3 sentences
            if len(sentence.strip()) > 50:  # Substantial content
                return sentence.strip()
        
        # Fallback to meta description
        return homepage.get('meta_description', '')
    
    def extract_career_info(self, page: Dict) -> List[str]:
        """Extract career-related information"""
        career_info = []
        content = page.get('main_content', '')
        
        # Look for career-related keywords
        if 'opportunity' in content.lower() or 'position' in content.lower():
            # Split content into sentences and find relevant ones
            sentences = content.split('.')
            for sentence in sentences:
                if any(word in sentence.lower() for word in ['career', 'job', 'position', 'opportunity', 'hiring']):
                    career_info.append(sentence.strip())
        
        return career_info

def main():
    """Main function to optimize the scraped data"""
    current_dir = os.path.dirname(__file__)
    data_file = os.path.join(current_dir, 'scrape_out', 'phoenix_all_content.json')
    
    if not os.path.exists(data_file):
        print(f"Data file not found: {data_file}")
        print("Please run scrape-phoenix.py first to generate the data file.")
        return
    
    optimizer = PhoenixDataOptimizer(data_file)
    optimized_data = optimizer.optimize_for_qa()
    
    # Save optimized data
    output_file = os.path.join(current_dir, 'scrape_out', 'phoenix_optimized_for_llm.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(optimized_data, f, ensure_ascii=False, indent=2)
    
    print(f"Optimized data saved to: {output_file}")
    
    # Print summary
    print("\n=== OPTIMIZATION SUMMARY ===")
    print(f"Total pages processed: {len(optimizer.pages)}")
    print(f"Products/Services found: {sum(len(v) for v in optimized_data['products_services'].values())}")
    print(f"Solutions found: {len(optimized_data['solutions']['by_industry']) + len(optimized_data['solutions']['by_use_case'])}")
    print(f"Key differentiators: {len(optimized_data['key_differentiators'])}")
    print(f"Search index entries: {len(optimized_data['search_index'])}")
    
    # Save a README for LLM usage
    readme_content = f"""# Phoenix Technologies Website Data

This dataset contains scraped and optimized content from Phoenix Technologies' website, structured for LLM question-answering.

## Data Structure

### Company Overview
- Company name, mission, and value proposition
- Key focus areas and differentiators

### Products & Services
- Infrastructure as a Service (IaaS)
- Platform as a Service (PaaS) 
- Software as a Service (SaaS)
- Professional Services
- Cybersecurity Solutions

### Solutions
- Industry-specific solutions (Healthcare, Education, Financial Services, Media)
- Use case solutions (AI Workloads, Data Center Exit, Critical Applications, CO2 Reduction)

### Search Index
- {len(optimized_data['search_index'])} searchable content entries
- Keywords and content snippets for each page

## Usage for LLM

This data is optimized to answer questions about:
- Phoenix Technologies' products and services
- Industry solutions and use cases
- Company information and differentiators
- Technical capabilities and specifications
- Partnership ecosystem
- Contact information

Generated on: {optimizer.raw_data.get('scraped_at', 'Unknown')}
Total pages: {len(optimizer.pages)}
"""
    
    readme_file = os.path.join(current_dir, 'scrape_out', 'README_LLM_DATA.md')
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"README saved to: {readme_file}")

if __name__ == "__main__":
    main()
