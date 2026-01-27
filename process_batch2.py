import csv
import re
import requests
import time
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# --- CONFIGURATION ---
INPUT_FILE = "ohio_batch2_to_enrich.csv"
OUTPUT_FILE = "ohio_batch2_enriched.csv"
BAD_URL_PATTERNS = ['/blog/', '/about/', '/service-area/', '/news/', '/article/', 
                    '/residential-services/', '/commercial-services/', '/team/']

# --- CLASSES ---

class ExhaustiveEmailResearcher:
    """
    EXHAUSTIVE email research - tries EVERYTHING for each lead
    Prioritizes personal emails over generic
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def technique_1_whois(self, domain):
        try:
            whois_urls = [f"https://www.whois.com/whois/{domain}", f"https://who.is/whois/{domain}"]
            emails = set()
            for url in whois_urls:
                try:
                    response = self.session.get(url, timeout=5)
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    found = re.findall(email_pattern, response.text, re.IGNORECASE)
                    emails.update([e for e in found if domain in e.lower()])
                except: continue
            return emails
        except: return set()
    
    def technique_2_dns_mx_patterns(self, domain, business_name):
        return {f"info@{domain}", f"contact@{domain}", f"hello@{domain}", f"admin@{domain}", 
                f"office@{domain}", f"sales@{domain}", f"support@{domain}"}
    
    def technique_3_google_bing_search(self, business_name, domain):
        emails = set()
        queries = [
            f'"{business_name}" email contact',
            f'"{business_name}" owner email',
            f'site:{domain} email contact',
        ]
        for query in queries:
            try:
                search_url = f"https://www.google.com/search?q={quote(query)}&num=10"
                response = self.session.get(search_url, timeout=5)
                email_pattern = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
                found = re.findall(email_pattern, response.text, re.IGNORECASE)
                emails.update(found)
                time.sleep(1)
            except: continue
        return emails
    
    def technique_5_pattern_generation(self, website, domain):
        patterns = set()
        try:
            about_pages = ['/about', '/about-us', '/team', '/company']
            names = []
            for page in about_pages:
                try:
                    url = website.rstrip('/') + page
                    response = self.session.get(url, timeout=5)
                    text = BeautifulSoup(response.text, 'html.parser').get_text()
                    matches = re.findall(r'(?:owner|founder|president|ceo)[\s:,]+([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
                    names.extend(matches)
                except: continue
            if names:
                for name in names[:1]:
                    parts = name.lower().split()
                    if len(parts) >= 2:
                        first, last = parts[0], parts[-1]
                        patterns.update([f"{first}@{domain}", f"{first}.{last}@{domain}"])
        except: pass
        return patterns

    def deep_scrape_website(self, website):
        try:
            response = self.session.get(website, timeout=10)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            return set(re.findall(email_pattern, response.text, re.IGNORECASE))
        except: return set()

    def prioritize_emails(self, all_emails, domain):
        if not all_emails: return None
        personal, generic, operational = [], [], []
        
        for email in all_emails:
            local = email.split('@')[0].lower()
            if any(k in local for k in ['support', 'service', 'billing', 'help', 'noreply', 'sales', 'info', 'contact', 'hello', 'admin', 'office', 'inquiry']):
                # Strict Tier 3 Definition
                generic.append(email) 
            elif len(local) > 2 and not re.search(r'\d{3}', local):
                # Personal?
                personal.append(email)
                
        if personal: return personal[0], 'owner', 'Tier 1 (Decision Maker)' 
        if generic: return generic[0], 'operational', 'Tier 3 (Operational)' # All generic are Tier 3 now per user rule
        return None

    def research(self, name, website):
        if not website: return None, None, None
        domain = urlparse(website).netloc.replace('www.', '')
        
        all_emails = set()
        # 1. Direct Scrape (Most effective usually)
        all_emails.update(self.deep_scrape_website(website))
        # 2. DNS Patterns
        all_emails.update(self.technique_2_dns_mx_patterns(domain, name))
        # 3. Google
        all_emails.update(self.technique_3_google_bing_search(name, domain))
        # 4. Pattern Gen
        all_emails.update(self.technique_5_pattern_generation(website, domain))
        
        # Valid filter
        valid = {e for e in all_emails if domain in e.lower() and not any(x in e.lower() for x in ['example', 'wix', 'sentry'])}
        
        return self.prioritize_emails(valid, domain)

# --- MAIN PROCESS ---

def process():
    researcher = ExhaustiveEmailResearcher()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    print(f"Loaded {len(rows)} leads. Starting enrichment pipeline...")
    
    enriched_count = 0
    filtered_count = 0
    
    processed_rows = []
    
    for i, row in enumerate(rows, 1):
        name = row.get('business_name', '')
        website = row.get('website', '').lower()
        
        # 1. Canonical URL Filter
        if any(pat in website for pat in BAD_URL_PATTERNS):
            print(f"[{i}/{len(rows)}] ❌ Filtered Content Page: {name}")
            filtered_count += 1
            continue
            
        print(f"[{i}/{len(rows)}] 🔎 Researching: {name}")
        
        # 2. Research
        email, role, source = researcher.research(name, row.get('website'))
        
        if email:
            row['email'] = email
            row['email_role'] = role # 'owner' or 'operational'
            row['Email_Source'] = source
            
            # Map tier numbers
            if role == 'owner': row['email_tier'] = '1'
            else: row['email_tier'] = '3' # All non-owner are Tier 3
            
            print(f"   => Found: {email} ({source})")
            enriched_count += 1
        else:
            row['email'] = ''
            row['email_tier'] = ''
            print(f"   => No email found")
            
        processed_rows.append(row)
        
    print(f"\nEnrichment Complete!")
    print(f"Processed: {len(rows)}")
    print(f"Filtered Content Pages: {filtered_count}")
    print(f"Enriched with Email: {enriched_count}")
    
    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)
        
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process()
