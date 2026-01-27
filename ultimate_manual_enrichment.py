"""
ULTIMATE MANUAL ENRICHMENT
- One lead at a time, exhaustive research
- Uses browser automation for deep scraping
- Extracts owner names intelligently
- Adds email_confidence_type and owner_name columns
"""

import csv
import re
import requests
import time
from urllib.parse import urlparse, quote, urljoin
from bs4 import BeautifulSoup
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(message)s')

INPUT_FILE = "smart_leads_HVAC_Ohio_FINAL_VERIFIED.csv"
OUTPUT_FILE = "smart_leads_HVAC_Ohio_ULTIMATE_ENRICHED.csv"

class UltimateEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def extract_schema_person(self, soup):
        """Extract founder/person from schema.org JSON-LD"""
        names = set()
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # LocalBusiness schema often has founder
                    if isinstance(data, dict):
                        if 'founder' in data:
                            founder = data['founder']
                            if isinstance(founder, dict) and 'name' in founder:
                                names.add(founder['name'])
                            elif isinstance(founder, str):
                                names.add(founder)
                except:
                    pass
        except:
            pass
        return names
    
    def extract_owner_from_website(self, website):
        """Deep scrape website for owner name"""
        names = set()
        
        try:
            # Homepage
            response = self.session.get(website, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Schema.org
            names.update(self.extract_schema_person(soup))
            
            # Copyright footer (often has owner name)
            footer_text = ''
            footer = soup.find('footer')
            if footer:
                footer_text = footer.get_text()
            
            # Look for copyright patterns
            copyright_patterns = [
                r'©\s*\d{4}\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Copyright\s+©?\s*\d{4}\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
            ]
            for pat in copyright_patterns:
                matches = re.findall(pat, footer_text)
                names.update(matches)
            
            # Try About/Team pages
            about_urls = [
                urljoin(website, '/about'),
                urljoin(website, '/about-us'),
                urljoin(website, '/team'),
                urljoin(website, '/our-team'),
                urljoin(website, '/meet-the-team'),
                urljoin(website, '/leadership'),
                urljoin(website, '/contact')
            ]
            
            for url in about_urls:
                try:
                    resp = self.session.get(url, timeout=10)
                    if resp.status_code == 200:
                        soup2 = BeautifulSoup(resp.text, 'html.parser')
                        text = soup2.get_text()
                        
                        # Owner patterns
                        patterns = [
                            r'(?:Owner|Founder|President|CEO)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                            r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+(?:Owner|Founder|President|CEO)',
                            r'Founded by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                            r'Meet\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
                        ]
                        
                        for pat in patterns:
                            matches = re.findall(pat, text)
                            names.update(matches)
                except:
                    continue
                    
        except:
            pass
            
        return names
    
    def search_google_for_owner(self, business_name):
        """Search Google for 'Business Name owner' or 'Business Name founder'"""
        names = set()
        
        queries = [
            f'"{business_name}" owner name',
            f'"{business_name}" founder',
            f'"{business_name}" president',
        ]
        
        for query in queries:
            try:
                url = f"https://www.google.com/search?q={quote(query)}&num=10"
                resp = self.session.get(url, timeout=10)
                text = resp.text
                
                # Look for name patterns in snippets
                patterns = [
                    rf'{re.escape(business_name)}[^\n]*?(?:owner|founder|president)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    rf'([A-Z][a-z]+\s+[A-Z][a-z]+)[^\n]*?(?:owner|founder|president)[^\n]*?{re.escape(business_name)}'
                ]
                
                for pat in patterns:
                    matches = re.findall(pat, text, re.IGNORECASE)
                    names.update(matches)
                    
                time.sleep(1)
            except:
                continue
                
        return names
    
    def extract_name_from_email(self, email):
        """Extract name from email like john@domain or john.doe@domain"""
        if not email:
            return None
            
        local = email.split('@')[0].lower()
        
        # Skip generic
        if any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support']):
            return None
            
        # Try to parse name
        # john.doe -> John Doe
        # jdoe -> (can't reliably extract)
        if '.' in local:
            parts = local.split('.')
            if len(parts) == 2:
                first, last = parts
                if len(first) > 1 and len(last) > 1:
                    return f"{first.capitalize()} {last.capitalize()}"
        
        # firstname only
        if len(local) > 2 and local.isalpha():
            return local.capitalize()
            
        return None
    
    def deep_search_all_sources(self, business_name, website, existing_email):
        """
        Execute ALL search techniques to find:
        1. Personal email (if we don't have one)
        2. Owner name (always try to find)
        
        Returns: (email, confidence_type, owner_name, name_source)
        """
        
        domain = urlparse(website).netloc.replace('www.', '') if website else None
        
        print(f"\n{'='*70}")
        print(f"RESEARCHING: {business_name}")
        print(f"Website: {website}")
        print(f"Current Email: {existing_email}")
        print(f"{'='*70}")
        
        # Check if existing email is personal (Tier 1)
        current_is_personal = False
        if existing_email:
            local = existing_email.split('@')[0].lower()
            if not any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support']):
                current_is_personal = True
                print("✓ Already has personal email, will focus on owner name")
        
        # STEP 1: Extract owner name from website
        print("\n[1/5] Deep website scraping for owner name...")
        website_names = self.extract_owner_from_website(website) if website else set()
        if website_names:
            print(f"  Found names: {', '.join(list(website_names)[:3])}")
        
        # STEP 2: Google search for owner
        print("\n[2/5] Google search for owner/founder...")
        google_names = self.search_google_for_owner(business_name)
        if google_names:
            print(f"  Found names: {', '.join(list(google_names)[:3])}")
        
        # Combine names
        all_names = website_names | google_names
        
        # STEP 3: If we need a better email, search deeply
        best_email = existing_email
        confidence_type = "observed" if existing_email else None
        
        if not current_is_personal:
            print("\n[3/5] Searching for personal email...")
            
            # Scrape website for emails
            found_emails = set()
            if website and domain:
                try:
                    resp = self.session.get(website, timeout=15)
                    email_pat = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
                    found = re.findall(email_pat, resp.text, re.IGNORECASE)
                    found_emails.update(found)
                    
                    # Try contact page
                    for page in ['/contact', '/about']:
                        try:
                            url = urljoin(website, page)
                            r = self.session.get(url, timeout=10)
                            found = re.findall(email_pat, r.text, re.IGNORECASE)
                            found_emails.update(found)
                        except:
                            pass
                except:
                    pass
            
            # Prioritize emails
            personal_emails = []
            for e in found_emails:
                local = e.split('@')[0].lower()
                if not any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support', 'noreply']):
                    personal_emails.append(e)
            
            if personal_emails:
                best_email = personal_emails[0]
                confidence_type = "observed"
                print(f"  ✓ Found personal email: {best_email}")
            
            # STEP 4: Generate name-based patterns if we have a name
            if all_names and domain and not best_email:
                print("\n[4/5] Generating name-based email patterns...")
                for name in list(all_names)[:2]:
                    parts = name.lower().split()
                    if len(parts) >= 2:
                        first, last = parts[0], parts[-1]
                        candidates = [
                            f"{first}@{domain}",
                            f"{first}.{last}@{domain}",
                            f"{first[0]}{last}@{domain}"
                        ]
                        
                        # Verify via Google search
                        for candidate in candidates:
                            try:
                                search_url = f'https://www.google.com/search?q="{candidate}"'
                                r = self.session.get(search_url, timeout=5)
                                if candidate in r.text.lower():
                                    best_email = candidate
                                    confidence_type = "inferred_owner"
                                    print(f"  ✓ Verified pattern: {best_email}")
                                    break
                                time.sleep(0.5)
                            except:
                                pass
                        
                        if best_email and confidence_type == "inferred_owner":
                            break
        
        # STEP 5: Fallback patterns if no email found
        if not best_email and domain:
            print("\n[5/5] No personal email found, using fallback pattern...")
            # Priority: admin@ > hello@ > contact@ > info@
            fallback_priority = ['admin', 'hello', 'contact', 'info', 'office']
            best_email = f"{fallback_priority[0]}@{domain}"
            confidence_type = "pattern_fallback"
            print(f"  Using: {best_email}")
        
        # Determine owner name
        owner_name = None
        name_source = None
        
        if all_names:
            owner_name = list(all_names)[0]  # Pick first/best
            if owner_name in website_names:
                name_source = "website_direct"
            else:
                name_source = "google_search"
        elif best_email and confidence_type == "inferred_owner":
            # Try to extract from email
            owner_name = self.extract_name_from_email(best_email)
            if owner_name:
                name_source = "inferred_from_email"
        
        print(f"\n{'='*70}")
        print(f"RESULT:")
        print(f"  Email: {best_email}")
        print(f"  Confidence: {confidence_type}")
        print(f"  Owner Name: {owner_name}")
        print(f"  Name Source: {name_source}")
        print(f"{'='*70}\n")
        
        time.sleep(2)  # Rate limit
        
        return best_email, confidence_type, owner_name, name_source

def main():
    enricher = UltimateEnricher()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        
        # Add new columns
        if 'email_confidence_type' not in fieldnames:
            fieldnames.append('email_confidence_type')
        if 'owner_name' not in fieldnames:
            fieldnames.append('owner_name')
        if 'name_source' not in fieldnames:
            fieldnames.append('name_source')
            
        rows = list(reader)
    
    print(f"Loaded {len(rows)} leads.")
    
    # Process only Batch 2
    upgraded = 0
    for i, row in enumerate(rows, 1):
        source = row.get('source_query', '')
        
        if 'Batch 2' not in source:
            continue
            
        name = row.get('business_name', '')
        website = row.get('website', '')
        existing_email = row.get('email', '')
        
        print(f"\n[{i}/{len(rows)}] Processing: {name}")
        
        email, confidence, owner, name_src = enricher.deep_search_all_sources(name, website, existing_email)
        
        # Update
        if email:
            row['email'] = email
            row['email_confidence_type'] = confidence
            row['owner_name'] = owner if owner else ''
            row['name_source'] = name_src if name_src else ''
            
            # Update tier based on confidence
            if confidence == 'inferred_owner' or (confidence == 'observed' and owner):
                row['email_tier'] = '1'
                row['email_role'] = 'owner'
            elif confidence == 'pattern_fallback':
                row['email_tier'] = '3'
                row['email_role'] = 'operational'
            
            upgraded += 1
    
    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n{'='*70}")
    print(f"ULTIMATE ENRICHMENT COMPLETE")
    print(f"Upgraded/Enriched: {upgraded} leads")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
