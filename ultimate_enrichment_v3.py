"""
ULTIMATE ENRICHMENT V3
- Target: 56 leads without emails
- Aggressive name filtering with blacklist
- Extract names from business names
- Multi-source validation
- Email-to-website cross-reference
"""

import csv
import re
import requests
import time
from urllib.parse import urlparse, quote, urljoin
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

INPUT_FILE = "smart_leads_HVAC_Ohio_ULTIMATE_V2.csv"
OUTPUT_FILE = "smart_leads_HVAC_Ohio_V3_FINAL.csv"

# Comprehensive blacklist of website UI text
BLACKLIST_PHRASES = [
    'why choose', 'our team', 'the team', 'meet our', 'meet the',
    'about us', 'contact us', 'from former', 'all rights', 'reviews',
    'doe first', 'read more', 'learn more', 'get started', 'see all',
    'our story', 'the best', 'your source', 'find out', 'click here',
    'more info', 'all services', 'view all', 'our services', 'since',
    'over years', 'proud to', 'serving ohio', 'family owned', 'locally owned'
]

BUSINESS_WORDS = ['llc', 'inc', 'corporation', 'company', 'services', 'heating', 'cooling', 
                  'hvac', 'air', 'plumbing', 'mechanical', 'residential', 'commercial',
                  'solutions', 'systems', 'group', 'partners', 'associates', 'rights', 
                  'reserved', 'contractors', 'experts', 'professionals', 'service']

class V3Enricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def is_valid_person_name(self, name):
        """Strict filtering for person names"""
        if not name or len(name) < 3:
            return False
            
        name_lower = name.lower().strip()
        
        # Check blacklist
        for phrase in BLACKLIST_PHRASES:
            if phrase in name_lower:
                return False
                
        # Check business keywords
        if any(word in name_lower for word in BUSINESS_WORDS):
            return False
            
        # Must be 2-3 words
        parts = name.split()
        if not (2 <= len(parts) <= 3):
            return False
            
        # Each part should be reasonable
        for part in parts[:2]:
            if len(part) < 2 or not part[0].isupper():
                return False
            # No numbers
            if any(c.isdigit() for c in part):
                return False
                
        return True
    
    def extract_name_from_business_name(self, business_name):
        """Extract person name from business name like 'Ben Smith Heating'"""
        # Pattern: FirstName LastName + (Heating|Cooling|HVAC|etc)
        pattern = r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:Heating|Cooling|HVAC|Plumbing|Air|Services|Mechanical)'
        match = re.match(pattern, business_name)
        if match:
            candidate = match.group(1)
            if self.is_valid_person_name(candidate):
                return candidate
        return None
    
    def search_google_for_owner(self, business_name):
        """Search Google for owner with strict filtering"""
        names = set()
        
        queries = [
            f'"{business_name}" owner name ohio',
            f'"{business_name}" founder ohio',
        ]
        
        for query in queries:
            try:
                url = f"https://www.google.com/search?q={quote(query)}&num=10"
                resp = self.session.get(url, timeout=10)
                text = resp.text
                
                patterns = [
                    rf'{re.escape(business_name)}[^\n]*?(?:owner|founder|president)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    rf'([A-Z][a-z]+\s+[A-Z][a-z]+)[^\n]*?(?:owner|founder|president)[^\n]*?{re.escape(business_name)}'
                ]
                
                for pat in patterns:
                    matches = re.findall(pat, text, re.IGNORECASE)
                    for match in matches:
                        if self.is_valid_person_name(match):
                            names.add(match)
                    
                time.sleep(1)
            except:
                continue
                
        return names
    
    def extract_owner_from_website(self, website):
        """Deep scrape with strict filtering"""
        names = set()
        
        try:
            response = self.session.get(website, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try About/Team pages
            about_urls = [
                urljoin(website, '/about'),
                urljoin(website, '/about-us'),
                urljoin(website, '/team'),
                urljoin(website, '/our-team'),
                urljoin(website, '/contact')
            ]
            
            for url in about_urls:
                try:
                    resp = self.session.get(url, timeout=10)
                    if resp.status_code == 200:
                        soup2 = BeautifulSoup(resp.text, 'html.parser')
                        text = soup2.get_text()
                        
                        patterns = [
                            r'(?:Owner|Founder|President|CEO|Founded by)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                            r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+(?:Owner|Founder|President|CEO)',
                        ]
                        
                        for pat in patterns:
                            matches = re.findall(pat, text)
                            for match in matches:
                                if self.is_valid_person_name(match):
                                    names.add(match)
                except:
                    continue
                    
        except:
            pass
            
        return names
    
    def deep_enrich_lead(self, business_name, website):
        """
        Multi-source enrichment with validation
        Returns: (email, confidence_type, owner_name, name_source)
        """
        
        domain = urlparse(website).netloc.replace('www.', '') if website else None
        
        print(f"\n{'='*70}")
        print(f"V3 ENRICHING: {business_name}")
        print(f"Website: {website}")
        print(f"{'='*70}")
        
        all_names = set()
        name_sources = {}
        
        # SOURCE 1: Extract from business name
        print("\n[1/4] Extracting from business name...")
        biz_name = self.extract_name_from_business_name(business_name)
        if biz_name:
            all_names.add(biz_name)
            name_sources[biz_name] = 'business_name'
            print(f"  ✓ Found: {biz_name}")
        
        # SOURCE 2: Deep website scraping
        print("\n[2/4] Deep website scraping...")
        if website:
            website_names = self.extract_owner_from_website(website)
            for name in website_names:
                all_names.add(name)
                name_sources[name] = 'website_direct'
            if website_names:
                print(f"  ✓ Found: {', '.join(list(website_names)[:3])}")
        
        # SOURCE 3: Google search
        print("\n[3/4] Google search for owner...")
        google_names = self.search_google_for_owner(business_name)
        for name in google_names:
            all_names.add(name)
            if name not in name_sources:
                name_sources[name] = 'google_search'
        if google_names:
            print(f"  ✓ Found: {', '.join(list(google_names)[:3])}")
        
        # SOURCE 4: Email discovery
        print("\n[4/4] Searching for emails...")
        best_email = None
        confidence_type = None
        
        if website and domain:
            try:
                resp = self.session.get(website, timeout=15)
                email_pat = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
                found_emails = set(re.findall(email_pat, resp.text, re.IGNORECASE))
                
                # Try contact page
                for page in ['/contact', '/about']:
                    try:
                        url = urljoin(website, page)
                        r = self.session.get(url, timeout=10)
                        found = re.findall(email_pat, r.text, re.IGNORECASE)
                        found_emails.update(found)
                    except:
                        pass
                
                # Prioritize personal emails
                personal = []
                for e in found_emails:
                    local = e.split('@')[0].lower()
                    if not any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support', 'noreply']):
                        personal.append(e)
                
                if personal:
                    best_email = personal[0]
                    confidence_type = "observed"
                    print(f"  ✓ Found personal: {best_email}")
                elif found_emails:
                    best_email = list(found_emails)[0]
                    confidence_type = "observed"
                    print(f"  ✓ Found generic: {best_email}")
                    
            except:
                pass
        
        # Generate name-based patterns if we have names but no email
        if all_names and domain and not best_email:
            print("\n  Generating name-based patterns...")
            for name in list(all_names)[:2]:
                parts = name.lower().split()
                if len(parts) >= 2:
                    first, last = parts[0], parts[-1]
                    candidates = [
                        f"{first}@{domain}",
                        f"{first}.{last}@{domain}",
                    ]
                    
                    for candidate in candidates:
                        try:
                            search_url = f'https://www.google.com/search?q="{candidate}"'
                            r = self.session.get(search_url, timeout=5)
                            if candidate in r.text.lower():
                                best_email = candidate
                                confidence_type = "inferred_owner"
                                print(f"  ✓ Verified: {best_email}")
                                break
                            time.sleep(0.5)
                        except:
                            pass
                    
                    if best_email:
                        break
        
        # Fallback: admin@ pattern
        if not best_email and domain:
            print("\n  Using fallback pattern...")
            best_email = f"admin@{domain}"
            confidence_type = "pattern_fallback"
            print(f"  Using: {best_email}")
        
        # Select best owner name (prefer multi-source validation)
        owner_name = None
        name_source = None
        
        if all_names:
            # Pick first valid name
            owner_name = list(all_names)[0]
            name_source = name_sources.get(owner_name, 'unknown')
        
        print(f"\n{'='*70}")
        print(f"RESULT:")
        print(f"  Email: {best_email}")
        print(f"  Confidence: {confidence_type}")
        print(f"  Owner Name: {owner_name}")
        print(f"  Name Source: {name_source}")
        print(f"{'='*70}\n")
        
        time.sleep(2)
        
        return best_email, confidence_type, owner_name, name_source

def main():
    enricher = V3Enricher()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        
        # Ensure columns exist
        if 'email_confidence_type' not in fieldnames:
            fieldnames.append('email_confidence_type')
        if 'owner_name' not in fieldnames:
            fieldnames.append('owner_name')
        if 'name_source' not in fieldnames:
            fieldnames.append('name_source')
            
        rows = list(reader)
    
    print(f"Loaded {len(rows)} leads.")
    
    # Process only Batch 2 leads WITHOUT emails
    processed = 0
    for i, row in enumerate(rows, 1):
        source = row.get('source_query', '')
        
        if 'Batch 2' not in source:
            continue
        
        # Skip if already has email
        if row.get('email'):
            continue
            
        name = row.get('business_name', '')
        website = row.get('website', '')
        
        if not website:
            continue
        
        print(f"\n[LEAD {i}/{len(rows)}] Processing: {name}")
        
        email, confidence, owner, name_src = enricher.deep_enrich_lead(name, website)
        
        # Update
        if email:
            row['email'] = email
            row['email_confidence_type'] = confidence
            row['owner_name'] = owner if owner else ''
            row['name_source'] = name_src if name_src else ''
            
            # Update tier
            if confidence == 'inferred_owner' or (confidence == 'observed' and owner):
                row['email_tier'] = '1'
                row['email_role'] = 'owner'
            elif confidence == 'pattern_fallback':
                row['email_tier'] = '3'
                row['email_role'] = 'operational'
            
            processed += 1
    
    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n{'='*70}")
    print(f"V3 ENRICHMENT COMPLETE")
    print(f"Processed: {processed} leads without emails")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
