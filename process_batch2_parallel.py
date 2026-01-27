import csv
import re
import requests
import time
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
import logging
import sys
import concurrent.futures
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# --- CONFIGURATION ---
INPUT_FILE = "ohio_batch2_to_enrich.csv"
OUTPUT_FILE = "ohio_batch2_enriched.csv"
BAD_URL_PATTERNS = ['/blog/', '/about/', '/service-area/', '/news/', '/article/', 
                    '/residential-services/', '/commercial-services/', '/team/']
MAX_WORKERS = 10  # Parallel threads

# Thread-safe writing
file_lock = threading.Lock()

# --- CLASSES ---

class ExhaustiveEmailResearcher:
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
                # Reduced sleep for parallel
                time.sleep(0.5)
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
                generic.append(email) 
            elif len(local) > 2 and not re.search(r'\d{3}', local):
                personal.append(email)
                
        if personal: return personal[0], 'owner', 'Tier 1 (Decision Maker)' 
        if generic: return generic[0], 'operational', 'Tier 3 (Operational)' 
        return None

    def research(self, name, website):
        if not website: return None, None, None
        domain = urlparse(website).netloc.replace('www.', '')
        if not domain: return None, None, None
        
        all_emails = set()
        all_emails.update(self.deep_scrape_website(website))
        all_emails.update(self.technique_2_dns_mx_patterns(domain, name))
        all_emails.update(self.technique_3_google_bing_search(name, domain))
        all_emails.update(self.technique_5_pattern_generation(website, domain))
        
        valid = {e for e in all_emails if domain in e.lower() and not any(x in e.lower() for x in ['example', 'wix', 'sentry'])}
        return self.prioritize_emails(valid, domain)

# --- WORKER ---

def process_one_lead(row, researcher, writer, counter, total):
    name = row.get('business_name', '')
    website = row.get('website', '').lower()
    
    # 1. Canonical Filter
    if any(pat in website for pat in BAD_URL_PATTERNS):
        return # Skip
        
    # 2. Research
    # print(f"Researching: {name}")
    try:
        email, role, source = researcher.research(name, row.get('website'))
    except:
        email, role, source = None, None, None
        
    if email:
        row['email'] = email
        row['email_role'] = role 
        row['Email_Source'] = source
        row['email_tier'] = '1' if role == 'owner' else '3'
    else:
        row['email'] = ''
        row['email_tier'] = ''
        
    # Write result immediately
    with file_lock:
        counter['processed'] += 1
        if email: counter['found'] += 1
        print(f"[{counter['processed']}/{total}] {name[:30]}... => {email if email else 'No email'}")
        writer.writerow(row)

# --- MAIN ---

def process():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    print(f"Loaded {len(rows)} leads. Starting parallel enrichment ({MAX_WORKERS} workers)...")
    
    # Initialize output file
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
    
    # Shared objects
    counter = {'processed': 0, 'found': 0}
    
    # Run
    with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Create a localized researcher for each call? Or share? 
            # Requests Session is not thread-safe if shared improperly, but we can make new one per task is safer or per thread.
            # Easiest: new researcher per task.
            futures = []
            for row in rows:
                futures.append(executor.submit(process_one_lead, row, ExhaustiveEmailResearcher(), writer, counter, len(rows)))
            
            concurrent.futures.wait(futures)
            
    print(f"\nEnrichment Complete!")
    print(f"Processed: {counter['processed']}")
    print(f"Enriched: {counter['found']}")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process()
