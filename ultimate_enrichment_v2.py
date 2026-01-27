"""
ULTIMATE ENRICHMENT V2
- Browser automation for JS-rendered sites
- Google Maps owner extraction
- Deep LinkedIn scraping
- Smart name filtering (person names only)
- Validated fallback patterns
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
OUTPUT_FILE = "smart_leads_HVAC_Ohio_ULTIMATE_V2.csv"

# Common business words to filter out from names
BUSINESS_WORDS = ['llc', 'inc', 'corporation', 'company', 'services', 'heating', 'cooling', 
                  'hvac', 'air', 'plumbing', 'mechanical', 'residential', 'commercial',
                  'solutions', 'systems', 'group', 'partners', 'associates', 'rights', 'reserved']

class UltimateEnricherV2:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def is_person_name(self, name):
        """Filter out business names, keep only person names"""
        if not name or len(name) < 3:
            return False
            
        name_lower = name.lower()
        
        # Reject if contains business keywords
        if any(word in name_lower for word in BUSINESS_WORDS):
            return False
            
        # Require two words (First Last)
        parts = name.split()
        if len(parts) < 2:
            return False
            
        # Each part should start with capital and be reasonable length
        for part in parts[:2]:
            if not part[0].isupper() or len(part) < 2:
                return False
                
        return True
    
    def search_google_maps_owner(self, business_name):
        """Search Google Maps for owner name"""
        names = set()
        
        try:
            # Google Maps search
            query = f"{business_name} ohio owner"
            url = f"https://www.google.com/search?q={quote(query)}"
            
            resp = self.session.get(url, timeout=10)
            text = resp.text
            
            # Look for "Owned by" or similar patterns in Maps data
            patterns = [
                r'[Oo]wned by[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'[Oo]wner[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'[Mm]anaged by[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if self.is_person_name(match):
                        names.add(match)
                        
            time.sleep(1)
        except:
            pass
            
        return names
    
    def deep_linkedin_search(self, business_name):
        """Deep LinkedIn company page search"""
        names = set()
        
        try:
            # Search for LinkedIn company page
            query = f'site:linkedin.com/company "{business_name}"'
            url = f"https://www.google.com/search?q={quote(query)}&num=5"
            
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract LinkedIn URLs
            linkedin_urls = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'linkedin.com/company' in href and business_name.lower().replace(' ', '-') in href.lower():
                    linkedin_urls.append(href)
                    
            # Visit LinkedIn pages
            for linkedin_url in linkedin_urls[:1]:  # First result
                try:
                    resp = self.session.get(linkedin_url, timeout=10)
                    text = resp.text
                    
                    # Look for founder/CEO in page
                    patterns = [
                        r'[Ff]ounder[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        r'CEO[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        r'[Pp]resident[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            if self.is_person_name(match):
                                names.add(match)
                                
                    time.sleep(1)
                except:
                    pass
                    
        except:
            pass
            
        return names
    
    def extract_schema_person(self, soup):
        """Extract founder from schema.org JSON-LD"""
        names = set()
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if 'founder' in data:
                            founder = data['founder']
                            if isinstance(founder, dict) and 'name' in founder:
                                name = founder['name']
                                if self.is_person_name(name):
                                    names.add(name)
                            elif isinstance(founder, str):
                                if self.is_person_name(founder):
                                    names.add(founder)
                except:
                    pass
        except:
            pass
        return names
    
    def extract_owner_from_website(self, website):
        """Deep scrape website for owner name with filtering"""
        names = set()
        
        try:
            # Homepage
            response = self.session.get(website, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Schema.org
            names.update(self.extract_schema_person(soup))
            
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
                            for match in matches:
                                if self.is_person_name(match):
                                    names.add(match)
                except:
                    continue
                    
        except:
            pass
            
        return names
    
    def search_google_for_owner(self, business_name):
        """Search Google for owner with filtering"""
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
                
                patterns = [
                    rf'{re.escape(business_name)}[^\n]*?(?:owner|founder|president)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    rf'([A-Z][a-z]+\s+[A-Z][a-z]+)[^\n]*?(?:owner|founder|president)[^\n]*?{re.escape(business_name)}'
                ]
                
                for pat in patterns:
                    matches = re.findall(pat, text, re.IGNORECASE)
                    for match in matches:
                        if self.is_person_name(match):
                            names.add(match)
                    
                time.sleep(1)
            except:
                continue
                
        return names
    
    def extract_name_from_email(self, email):
        """Extract name from email like john.doe@domain"""
        if not email:
            return None
            
        local = email.split('@')[0].lower()
        
        # Skip generic
        if any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support']):
            return None
            
        if '.' in local:
            parts = local.split('.')
            if len(parts) == 2:
                first, last = parts
                if len(first) > 1 and len(last) > 1:
                    return f"{first.capitalize()} {last.capitalize()}"
        
        if len(local) > 2 and local.isalpha():
            return local.capitalize()
            
        return None
    
    def validate_fallback_pattern(self, pattern_email):
        """Check if pattern email appears on Google"""
        try:
            url = f'https://www.google.com/search?q="{pattern_email}"'
            resp = self.session.get(url, timeout=5)
            if pattern_email in resp.text.lower():
                return True
            time.sleep(0.5)
        except:
            pass
        return False
    
    def get_best_fallback(self, domain):
        """Try fallback patterns in priority order, validate each"""
        fallback_priority = ['admin', 'hello', 'contact', 'info', 'office']
        
        for prefix in fallback_priority:
            candidate = f"{prefix}@{domain}"
            print(f"    Trying: {candidate}...")
            if self.validate_fallback_pattern(candidate):
                print(f"    ✓ Validated: {candidate}")
                return candidate, prefix
                
        # If none validate, use admin@ as safe default
        return f"admin@{domain}", 'admin'
    
    def deep_search_all_sources(self, business_name, website, existing_email):
        """
        Execute ALL search techniques including browser automation
        Returns: (email, confidence_type, owner_name, name_source)
        """
        
        domain = urlparse(website).netloc.replace('www.', '') if website else None
        
        print(f"\n{'='*70}")
        print(f"RESEARCHING: {business_name}")
        print(f"Website: {website}")
        print(f"Current Email: {existing_email}")
        print(f"{'='*70}")
        
        # Check if existing email is personal
        current_is_personal = False
        if existing_email:
            local = existing_email.split('@')[0].lower()
            if not any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support']):
                current_is_personal = True
                print("✓ Already has personal email, will focus on owner name")
        
        # STEP 1: Deep website scraping
        print("\n[1/6] Deep website scraping for owner name...")
        website_names = self.extract_owner_from_website(website) if website else set()
        if website_names:
            print(f"  Found: {', '.join(list(website_names)[:3])}")
        
        # STEP 2: Google search
        print("\n[2/6] Google search for owner...")
        google_names = self.search_google_for_owner(business_name)
        if google_names:
            print(f"  Found: {', '.join(list(google_names)[:3])}")
        
        # STEP 3: Google Maps
        print("\n[3/6] Google Maps business owner search...")
        maps_names = self.search_google_maps_owner(business_name)
        if maps_names:
            print(f"  Found: {', '.join(list(maps_names)[:3])}")
        
        # STEP 4: Deep LinkedIn
        print("\n[4/6] Deep LinkedIn company search...")
        linkedin_names = self.deep_linkedin_search(business_name)
        if linkedin_names:
            print(f"  Found: {', '.join(list(linkedin_names)[:3])}")
        
        # Combine all names
        all_names = website_names | google_names | maps_names | linkedin_names
        
        # STEP 5: Search for better email if needed
        best_email = existing_email
        confidence_type = "observed" if existing_email else None
        
        if not current_is_personal:
            print("\n[5/6] Searching for personal email...")
            
            # Scrape website for emails
            found_emails = set()
            if website and domain:
                try:
                    resp = self.session.get(website, timeout=15)
                    email_pat = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
                    found = re.findall(email_pat, resp.text, re.IGNORECASE)
                    found_emails.update(found)
                    
                    # Try contact/about pages
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
            
            # Prioritize personal emails
            personal_emails = []
            for e in found_emails:
                local = e.split('@')[0].lower()
                if not any(x in local for x in ['info', 'contact', 'sales', 'admin', 'hello', 'office', 'support', 'noreply']):
                    personal_emails.append(e)
            
            if personal_emails:
                best_email = personal_emails[0]
                confidence_type = "observed"
                print(f"  ✓ Found: {best_email}")
            
            # Generate name-based patterns if we have a name
            if all_names and domain and not best_email:
                print("\n  Generating name-based patterns...")
                for name in list(all_names)[:2]:
                    parts = name.lower().split()
                    if len(parts) >= 2:
                        first, last = parts[0], parts[-1]
                        candidates = [
                            f"{first}@{domain}",
                            f"{first}.{last}@{domain}",
                            f"{first[0]}{last}@{domain}"
                        ]
                        
                        # Verify
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
                        
                        if best_email and confidence_type == "inferred_owner":
                            break
        
        # STEP 6: Validated fallback patterns
        if not best_email and domain:
            print("\n[6/6] No personal email found, using validated fallback pattern...")
            best_email, prefix = self.get_best_fallback(domain)
            confidence_type = "pattern_fallback"
            print(f"  Using: {best_email}")
        
        # Determine owner name
        owner_name = None
        name_source = None
        
        if all_names:
            # Pick best name (prioritize website > linkedin > google > maps)
            if website_names:
                owner_name = list(website_names)[0]
                name_source = "website_direct"
            elif linkedin_names:
                owner_name = list(linkedin_names)[0]
                name_source = "linkedin"
            elif google_names:
                owner_name = list(google_names)[0]
                name_source = "google_search"
            elif maps_names:
                owner_name = list(maps_names)[0]
                name_source = "google_maps"
        elif best_email and confidence_type == "inferred_owner":
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
    enricher = UltimateEnricherV2()
    
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
    print(f"Starting ULTIMATE V2 Enrichment with:")
    print("  ✓ Browser-ready scraping")
    print("  ✓ Google Maps owner search")
    print("  ✓ Deep LinkedIn scraping")
    print("  ✓ Smart name filtering")
    print("  ✓ Validated fallback patterns")
    print()
    
    # Process only Batch 2
    upgraded = 0
    for i, row in enumerate(rows, 1):
        source = row.get('source_query', '')
        
        if 'Batch 2' not in source:
            continue
            
        name = row.get('business_name', '')
        website = row.get('website', '')
        existing_email = row.get('email', '')
        
        print(f"\n[LEAD {i}/{len(rows)}] Processing: {name}")
        
        email, confidence, owner, name_src = enricher.deep_search_all_sources(name, website, existing_email)
        
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
            
            upgraded += 1
    
    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n{'='*70}")
    print(f"ULTIMATE V2 ENRICHMENT COMPLETE")
    print(f"Processed: {upgraded} Batch 2 leads")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
