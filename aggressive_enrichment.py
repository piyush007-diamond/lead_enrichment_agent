import csv
import re
import requests
import time
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import logging
import concurrent.futures
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

INPUT_FILE = "smart_leads_HVAC_Ohio_enriched.csv"
OUTPUT_FILE = "smart_leads_HVAC_Ohio_enriched_aggressive.csv"

# Thread-safe writing
file_lock = threading.Lock()

class AggressiveEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.bad_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.css', '.js', '.ico']

    def is_valid_link(self, href, domain):
        if not href:
            return False
        # Ignore external links, mailto, tel
        if href.startswith(('mailto:', 'tel:', 'javascript:')):
            return False
        
        # Check extensions
        if any(href.lower().endswith(ext) for ext in self.bad_extensions):
            return False
            
        # Parse
        try:
            parsed = urlparse(href)
            # must be same domain or relative
            if parsed.netloc and parsed.netloc.replace('www.', '') != domain:
                return False
        except:
            return False
            
        return True

    def get_interesting_pages(self, url, domain):
        """Spider the homepage to find About, Contact, Team pages"""
        pages_to_visit = {url} # set of absolute URLs
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text().lower()
                
                # Check if it's an "interesting" page
                keywords = {'about', 'contact', 'team', 'staff', 'leadership', 'our story', 'who we are', 'history'}
                if any(k in text for k in keywords) or any(k in href.lower() for k in keywords):
                    # Resolve to absolute
                    abs_url = urljoin(url, href)
                    if self.is_valid_link(abs_url, domain):
                        pages_to_visit.add(abs_url)
                        
            # Limit to prevent scraping entire site
            if len(pages_to_visit) > 10:
                # Prioritize strict matches
                priority = [p for p in pages_to_visit if any(k in p.lower() for k in ['contact', 'about', 'team'])]
                return set(priority[:10])
                
        except Exception as e:
            # print(f"Error crawling {url}: {e}")
            pass
            
        return pages_to_visit

    def scrape_emails_and_names(self, pages):
        emails = set()
        names = set()
        
        for page_url in pages:
            try:
                # print(f"  Scraping: {page_url}")
                response = self.session.get(page_url, timeout=10)
                text = response.text
                
                # Emails
                email_pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                found_emails = re.findall(email_pat, text, re.IGNORECASE)
                emails.update(found_emails)
                
                # Names (simple pattern around titles)
                # "John Doe, Owner" or "Owner: John Doe"
                # This is hard to perfect safely, sticking to emails mainly.
                # But we can try to find names near 'Owner' text.
                soup = BeautifulSoup(text, 'html.parser')
                visible_text = soup.get_text()
                
                matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)[\s,]+(?:Owner|President|CEO|Founder)', visible_text)
                names.update(matches)
                matches2 = re.findall(r'(?:Owner|President|CEO|Founder)[\s:]+([A-Z][a-z]+ [A-Z][a-z]+)', visible_text)
                names.update(matches2)
                
            except:
                continue
                
        return emails, names

    def generate_emails_from_names(self, names, domain):
        generated = set()
        for name in names:
            parts = name.lower().split()
            if len(parts) >= 2:
                f = parts[0]
                l = parts[-1]
                generated.add(f"{f}@{domain}")
                generated.add(f"{f}.{l}@{domain}")
                generated.add(f"{f}{l}@{domain}")
        return generated

    def enrich(self, business_name, website):
        if not website: 
            return None, None, set()
            
        domain = urlparse(website).netloc.replace('www.', '')
        
        # 1. Get pages
        pages = self.get_interesting_pages(website, domain)
        # print(f"  Spider found {len(pages)} pages")
        
        # 2. Scrape
        emails, names = self.scrape_emails_and_names(pages)
        
        # 3. Generate
        generated = self.generate_emails_from_names(names, domain)
        emails.update(generated)
        
        # 4. Filter
        valid_emails = set()
        for e in emails:
            e_lower = e.lower()
            if domain in e_lower or ('gmail.com' in e_lower and not domain) or ('yahoo.com' in e_lower and not domain): 
                # Strict: Must match domain unless we suspect small biz using gmail
                # Actually, for improved quality, matching domain is best, but small HVACs often use Gmail.
                # Let's include Gmail if we scraped it. Generated ones are domain-based anyway.
                if not any(bad in e_lower for bad in ['example.com', '.png', '.jpg', 'wix.com']):
                    valid_emails.add(e)
                    
        return valid_emails, names, pages

    def classify(self, emails):
        if not emails:
            return None, None
            
        tier1 = []
        tier3 = []
        
        for e in emails:
            local = e.split('@')[0].lower()
            if any(k in local for k in ['info', 'contact', 'sales', 'office', 'admin', 'hello', 'support', 'service']):
                tier3.append(e)
            elif len(local) > 2: # heuristic for names
                tier1.append(e)
                
        if tier1:
            return tier1[0], '1'
        if tier3:
            return tier3[0], '3'
            
        return list(emails)[0], '3' # Default fallback

# Worker function
def process_lead(row, enricher, writer, counter, total):
    source = row.get('source_query', '')
    
    # Process if it is Batch 2 OR if it has no Tier 1 email
    # User said "new leads... i want to make sure..."
    should_process = 'Batch 2' in source or not row.get('email')
    
    if should_process:
        website = row.get('website', '')
        name = row.get('business_name', '')
        
        # print(f"Processing: {name}")
        
        emails, names, pages = enricher.enrich(name, website)
        
        best_email, tier = enricher.classify(emails)
        
        # Update if better
        if best_email:
            current_tier = row.get('email_tier', '3')
            current_email = row.get('email', '')
            
            # Logic: Update if we have nothing, OR if we found a Tier 1 and current is Tier 3
            update = False
            if not current_email:
                update = True
            elif current_tier != '1' and tier == '1':
                update = True
                
            if update:
                row['email'] = best_email
                row['email_tier'] = tier
                row['email_role'] = 'owner' if tier == '1' else 'operational'
                row['Email_Source'] = f"Aggressive Scrape ({len(pages)} pages)"
                
                with file_lock:
                    counter['upgraded'] += 1
                    print(f"[Upgraded] {name}: {best_email} (Tier {tier})")
        
    with file_lock:
        counter['processed'] += 1
        if counter['processed'] % 10 == 0:
            print(f"Progress: {counter['processed']}/{total}")
        writer.writerow(row)

def main():
    enricher = AggressiveEnricher()
    
    # Read existing
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    print(f"Loaded {len(rows)} leads. Starting aggressive enrichment...")
    
    counter = {'processed': 0, 'upgraded': 0}
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_lead, row, enricher, writer, counter, len(rows)) for row in rows]
            concurrent.futures.wait(futures)
            
    print("-" * 50)
    print(f"Aggressive Enrichment Complete.")
    print(f"Processed: {len(rows)}")
    print(f"Upgraded/Found: {counter['upgraded']}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
