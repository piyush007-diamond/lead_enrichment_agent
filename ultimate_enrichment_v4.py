"""
V4 LAST-RESORT ENRICHMENT
For 56 leads with NO websites
- Phone number reverse lookup
- Domain inference (businessname.com)
- Deep social media search
- Location-based Google search
"""

import csv
import re
import requests
import time
from urllib.parse import quote
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

INPUT_FILE = "smart_leads_HVAC_Ohio_ULTIMATE_V2.csv"
OUTPUT_FILE = "smart_leads_HVAC_Ohio_V4_COMPLETE.csv"

class V4LastResortEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_phone_for_website(self, phone, business_name):
        """Reverse phone lookup to find website"""
        if not phone:
            return None
            
        try:
            # Clean phone
            phone_clean = re.sub(r'[^\d]', '', phone)
            
            # Google search with phone
            query = f'"{phone}" OR "{phone_clean}" {business_name}'
            url = f"https://www.google.com/search?q={quote(query)}"
            resp = self.session.get(url, timeout=10)
            
            # Look for URLs
            url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'
            urls = re.findall(url_pattern, resp.text)
            
            # Filter to likely business domains
            for domain in urls:
                domain_lower = domain.lower()
                if any(x in domain_lower for x in ['facebook', 'yelp', 'google', 'youtube', 'twitter', 'linkedin']):
                    continue
                # Likely a business website
                return f"https://{domain}"
                
            time.sleep(1)
        except:
            pass
        return None
    
    def infer_domain(self, business_name):
        """Try to infer domain from business name"""
        # Clean business name
        name = business_name.lower()
        # Remove common words
        name = re.sub(r'\b(llc|inc|corporation|company|services|heating|cooling|hvac|air|plumbing|mechanical|ohio)\b', '', name)
        name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
        name = name.strip().replace(' ', '')
        
        if len(name) < 3:
            return None
        
        # Try common patterns
        candidates = [
            f"{name}.com",
            f"{name}hvac.com",
            f"{name}ohio.com",
        ]
        
        for domain in candidates:
            try:
                # Check if domain exists
                url = f"http://{domain}"
                resp = self.session.head(url, timeout=5, allow_redirects=True)
                if resp.status_code < 400:
                    return url
            except:
                pass
        
        return None
    
    def search_facebook(self, business_name):
        """Deep Facebook search"""
        try:
            query = f'site:facebook.com "{business_name}" Ohio HVAC'
            url = f"https://www.google.com/search?q={quote(query)}"
            resp = self.session.get(url, timeout=10)
            
            # Look for Facebook page URL
            fb_pattern = r'https://(?:www\.)?facebook\.com/([^/"\s]+)'
            matches = re.findall(fb_pattern, resp.text)
            if matches:
                fb_page = f"https://facebook.com/{matches[0]}"
                
                # Try to extract email from Facebook page
                try:
                    fb_resp = self.session.get(fb_page, timeout=10)
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, fb_resp.text, re.IGNORECASE)
                    if emails:
                        return emails[0], fb_page
                except:
                    pass
                
                return None, fb_page
            
            time.sleep(1)
        except:
            pass
        return None, None
    
    def google_business_search(self, business_name):
        """Search Google for business website"""
        try:
            query = f'"{business_name}" Ohio HVAC heating cooling'
            url = f"https://www.google.com/search?q={quote(query)}"
            resp = self.session.get(url, timeout=10)
            
            # Extract URLs
            url_pattern = r'https?://(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'
            urls = re.findall(url_pattern, resp.text)
            
            # Filter business URLs
            for domain in urls:
                domain_lower = domain.lower()
                # Skip social/directory sites
                if any(x in domain_lower for x in ['facebook', 'yelp', 'google', 'bbb', 'yellowpages', 'homeadvisor', 'angi']):
                    continue
                return f"https://{domain}"
            
            time.sleep(1)
        except:
            pass
        return None
    
    def enrich_no_website_lead(self, business_name, phone):
        """Try everything to find website/email"""
        print(f"\n{'='*70}")
        print(f"V4 LAST-RESORT: {business_name}")
        print(f"Phone: {phone}")
        print(f"{'='*70}")
        
        website = None
        email = None
        source = None
        
        # METHOD 1: Phone search
        print("\n[1/4] Phone number reverse lookup...")
        website = self.search_phone_for_website(phone, business_name)
        if website:
            print(f"  ✓ Found website: {website}")
            source = "phone_lookup"
        
        # METHOD 2: Domain inference
        if not website:
            print("\n[2/4] Inferring domain from business name...")
            website = self.infer_domain(business_name)
            if website:
                print(f"  ✓ Inferred: {website}")
                source = "domain_inference"
        
        # METHOD 3: Google search
        if not website:
            print("\n[3/4] Google business search...")
            website = self.google_business_search(business_name)
            if website:
                print(f"  ✓ Found: {website}")
                source = "google_search"
        
        # METHOD 4: Facebook
        if not email:
            print("\n[4/4] Facebook page search...")
            fb_email, fb_page = self.search_facebook(business_name)
            if fb_email:
                email = fb_email
                source = "facebook"
                print(f"  ✓ Found email on Facebook: {email}")
            elif fb_page:
                print(f"  ✓ Found Facebook page (no email): {fb_page}")
        
        # If we found website, try to get email
        if website and not email:
            try:
                print("\n  Scraping website for email...")
                resp = self.session.get(website, timeout=10)
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, resp.text, re.IGNORECASE)
                
                # Try to get domain from website
                from urllib.parse import urlparse
                domain = urlparse(website).netloc.replace('www.', '')
                
                # Filter to domain emails
                domain_emails = [e for e in emails if domain in e.lower()]
                if domain_emails:
                    email = domain_emails[0]
                    print(f"  ✓ Scraped: {email}")
                elif not email and domain:
                    # Fallback pattern
                    email = f"admin@{domain}"
                    source = f"{source}_pattern"
                    print(f"  Using pattern: {email}")
            except:
                pass
        
        print(f"\n{'='*70}")
        print(f"RESULT:")
        print(f"  Website: {website or 'NOT FOUND'}")
        print(f"  Email: {email or 'NOT FOUND'}")
        print(f"  Source: {source or 'none'}")
        print(f"{'='*70}\n")
        
        time.sleep(2)
        
        return website, email, source

def main():
    enricher = V4LastResortEnricher()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    
    # Ensure Email_Source column
    if 'Email_Source' not in fieldnames:
        fieldnames.append('Email_Source')
    
    print(f"Loaded {len(rows)} leads.")
    
    # Process Batch 2 leads without email AND without website
    processed = 0
    found = 0
    
    for i, row in enumerate(rows, 1):
        source = row.get('source_query', '')
        
        if 'Batch 2' not in source:
            continue
        
        # Skip if has email OR website
        if row.get('email') or row.get('website'):
            continue
        
        name = row.get('business_name', '')
        phone = row.get('phone', '')
        
        print(f"\n[LEAD {i}/{len(rows)}] {name}")
        
        website, email, src = enricher.enrich_no_website_lead(name, phone)
        
        if website or email:
            if website:
                row['website'] = website
            if email:
                row['email'] = email
                row['email_tier'] = '3'  # Inferred/pattern
                row['email_role'] = 'operational'
                row['Email_Source'] = f"V4_{src}"
                row['email_confidence_type'] = 'inferred' if src in ['phone_lookup', 'domain_inference'] else 'observed'
            found += 1
        
        processed += 1
    
    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n{'='*70}")
    print(f"V4 LAST-RESORT ENRICHMENT COMPLETE")
    print(f"Processed: {processed} leads")
    print(f"Found new data: {found} leads")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
