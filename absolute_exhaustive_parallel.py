import csv
import re
import requests
import time
from urllib.parse import urlparse, quote, urljoin
from bs4 import BeautifulSoup
import logging
import concurrent.futures
import threading
import sys
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

INPUT_FILE = "smart_leads_HVAC_Ohio_enriched.csv"
OUTPUT_FILE = "smart_leads_HVAC_Ohio_enriched_absolute_final.csv"

# Thread control
file_lock = threading.Lock()
MAX_WORKERS = 5

class UltimateResearcher:
    def __init__(self):
        # Each thread gets its own session
        self.session = requests.Session()
        self.session.headers.update({
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def random_sleep(self, min_s=1, max_s=3):
        time.sleep(random.uniform(min_s, max_s))

    def search_google(self, query):
        try:
            url = f"https://www.google.com/search?q={quote(query)}&num=10"
            r = self.session.get(url, timeout=10)
            return r.text
        except: return ""

    def get_whois_emails(self, domain):
        emails = set()
        try:
            r = self.session.get(f"https://www.whois.com/whois/{domain}", timeout=10)
            emails.update(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r.text, re.IGNORECASE))
        except: pass
        return {e for e in emails if domain in e.lower()}

    def get_dns_patterns(self, domain):
        return {f"info@{domain}", f"sales@{domain}", f"admin@{domain}", f"hello@{domain}"}

    def search_company_email(self, name, domain):
        emails = set()
        queries = [f'"{name}" email', f'"{name}" contact', f'site:{domain} email']
        for q in queries:
            text = self.search_google(q)
            emails.update(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text, re.IGNORECASE))
            self.random_sleep(0.5, 1.5)
        return emails

    def search_directories(self, name, domain):
        emails = set()
        queries = [f'site:bbb.org "{name}" email', f'site:yelp.com "{name}" email']
        for q in queries:
            text = self.search_google(q)
            emails.update(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text, re.IGNORECASE))
            self.random_sleep(0.5, 1.5)
        return emails

    def generate_patterns(self, website, domain):
        patterns = set()
        names = set()
        pages = [website, urljoin(website, '/about'), urljoin(website, '/team'), urljoin(website, '/contact')]
        for p in pages:
            try:
                r = self.session.get(p, timeout=5)
                matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)[\s,]+(?:Owner|President|CEO|Founder)', r.text)
                names.update(matches)
            except: pass
        
        for n in names:
            parts = n.lower().split()
            if len(parts) >= 2:
                f, l = parts[0], parts[-1]
                patterns.add(f"{f}@{domain}")
                patterns.add(f"{f}.{l}@{domain}")
        return patterns

    def deep_social_search(self, name, domain, platform):
        emails = set()
        queries = [
            f'site:{platform}.com "{name}" email', 
            f'site:{platform}.com "{name}" owner',
            f'site:{platform}.com "{name}" "{domain}"'
        ]
        for q in queries:
            text = self.search_google(q)
            found = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text, re.IGNORECASE)
            for e in found:
                if domain in e.lower() or any(x in e.lower() for x in ['gmail.com', 'yahoo.com', 'outlook.com']) and name.split()[0].lower() in e.lower():
                    emails.add(e)
            self.random_sleep(0.5, 1.5)
        return emails

    def process_lead(self, name, website):
        domain = ""
        if website:
            try: domain = urlparse(website).netloc.replace('www.', '')
            except: pass
            
        all_emails = set()
        if domain: 
            all_emails.update(self.get_whois_emails(domain))
            all_emails.update(self.get_dns_patterns(domain))
            all_emails.update(self.search_company_email(name, domain))
            all_emails.update(self.search_directories(name, domain))
            if website: all_emails.update(self.generate_patterns(website, domain))
        
        # Deep Social (Run even if no domain, use name)
        social_domain = domain if domain else name.replace(" ", "").lower() + ".com"
        all_emails.update(self.deep_social_search(name, social_domain, "facebook"))
        all_emails.update(self.deep_social_search(name, social_domain, "linkedin"))
        
        # Clean
        valid = set()
        for e in all_emails:
            e = e.lower().strip('.')
            if any(x in e for x in ['wix.com', 'sentry.io', 'example.com', '.png', '.jpg']): continue
            valid.add(e)
        return valid

    def classify_email(self, email):
        local = email.split('@')[0].lower()
        if any(x in local for x in ['sales', 'info', 'contact', 'admin', 'office', 'support']):
            return '3', 'operational'
        return '1', 'owner'

def worker(row, writer, counter, total):
    name = row.get('business_name', '')
    website = row.get('website', '')
    source = row.get('source_query', '')
    
    # Process only Batch 2
    if 'Batch 2' not in source:
        return
        
    start = time.time()
    researcher = UltimateResearcher() # New researcher per task for thread safety of session
    
    # print(f"Processing: {name}")
    emails = researcher.process_lead(name, website)
    
    best_email = None
    best_tier = '9'
    
    for e in emails:
        tier, role = researcher.classify_email(e)
        if best_email is None or tier < best_tier:
            best_email = e
            best_tier = tier
            
    if best_email:
        # Update logic: keep explicit owner if we have it, else upgrade
        curr_tier = row.get('email_tier', '3')
        if not row.get('email') or (curr_tier != '1' and best_tier == '1'):
             row['email'] = best_email
             row['email_tier'] = best_tier
             row['email_role'] = 'owner' if best_tier == '1' else 'operational'
             row['Email_Source'] = 'Absolute Exhaustive'
    
    duration = time.time() - start
    
    with file_lock:
        counter['processed'] += 1
        pct = (counter['processed'] / total) * 100
        if best_email: counter['found'] += 1
        print(f"[{counter['processed']}/{total} {pct:.1f}%] {name} => {best_email} ({duration:.1f}s)")
        writer.writerow(row)
        
def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    batch2_rows = [r for r in rows if 'Batch 2' in r.get('source_query', '')]
    other_rows = [r for r in rows if 'Batch 2' not in r.get('source_query', '')]
    
    print(f"Loaded {len(rows)} leads. Processing {len(batch2_rows)} Batch 2 leads with {MAX_WORKERS} workers.")
    
    counter = {'processed': 0, 'found': 0}
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write pre-existing non-batch2 rows immediately
        for r in other_rows:
            writer.writerow(r)
            
        # Process Batch 2 in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker, row, writer, counter, len(batch2_rows)) for row in batch2_rows]
            concurrent.futures.wait(futures)
            
    print("Done.")

if __name__ == "__main__":
    main()
