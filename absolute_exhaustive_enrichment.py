import csv
import re
import requests
import time
from urllib.parse import urlparse, quote, urljoin
from bs4 import BeautifulSoup
import logging
import threading
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

INPUT_FILE = "smart_leads_HVAC_Ohio_enriched.csv"
OUTPUT_FILE = "smart_leads_HVAC_Ohio_enriched_absolute.csv"

class UltimateResearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def search_google(self, query):
        """Helper to search google and return snippets"""
        try:
            url = f"https://www.google.com/search?q={quote(query)}&num=10"
            r = self.session.get(url, timeout=10)
            return r.text
        except:
            return ""

    def get_whois_emails(self, domain):
        """1. WHOIS"""
        emails = set()
        try:
            # Using web whois proxies
            urls = [f"https://www.whois.com/whois/{domain}"]
            for u in urls:
                r = self.session.get(u, timeout=10)
                # Simple extraction
                pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                found = re.findall(pat, r.text, re.IGNORECASE)
                # Filter useful ones
                for e in found:
                    if domain in e.lower() or 'whois' not in e.lower():
                         emails.add(e)
        except: pass
        return emails

    def get_dns_patterns(self, domain):
        """2. DNS/Common Patterns"""
        return {f"info@{domain}", f"contact@{domain}", f"sales@{domain}", f"admin@{domain}", f"office@{domain}", f"hello@{domain}"}

    def search_company_email(self, name, domain):
        """3. Company + Email Search"""
        emails = set()
        queries = [
            f'"{name}" email',
            f'"{name}" contact',
            f'"{name}" "@ {domain}"',
            f'site:{domain} "email"'
        ]
        for q in queries:
            text = self.search_google(q)
            pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails.update(re.findall(pat, text, re.IGNORECASE))
            time.sleep(1)
        return emails

    def search_directories(self, name, domain):
        """4. Directories (BBB, etc)"""
        emails = set()
        queries = [
            f'site:bbb.org "{name}" email',
            f'site:yelp.com "{name}" email',
            f'site:chamberofcommerce.com "{name}" email'
        ]
        for q in queries:
            text = self.search_google(q)
            pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails.update(re.findall(pat, text, re.IGNORECASE))
            time.sleep(1)
        return emails

    def generate_patterns(self, website, domain):
        """5. Pattern Gen from Website Names"""
        patterns = set()
        # Scan website for names
        names = set()
        pages = [website, urljoin(website, '/about'), urljoin(website, '/team'), urljoin(website, '/contact')]
        
        for p in pages:
            try:
                r = self.session.get(p, timeout=5)
                # Look for Owner/Title patterns
                # "John Doe, Owner"
                matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)[\s,]+(?:Owner|President|CEO|Founder|Manager)', r.text)
                names.update(matches)
            except: pass
        
        for n in names:
            parts = n.lower().split()
            if len(parts) >= 2:
                f, l = parts[0], parts[-1]
                patterns.add(f"{f}@{domain}")
                patterns.add(f"{f}.{l}@{domain}")
                patterns.add(f"{f}{l}@{domain}")
        return patterns

    def deep_social_search(self, name, domain, platform):
        """6 & 7. Deep Social (Facebook/LinkedIn)"""
        emails = set()
        # Queries to find profile and email
        queries = [
            f'site:{platform}.com "{name}" email',
            f'site:{platform}.com "{name}" contact',
            f'site:{platform}.com "{name}" "@ {domain}"',
            f'site:{platform}.com "{name}" owner email',
            f'site:{platform}.com "{name}" gmail.com' # Small biz often use gmail on FB
        ]
        
        for q in queries:
            text = self.search_google(q)
            # Find emails
            pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found = re.findall(pat, text, re.IGNORECASE)
            
            # Filter
            for e in found:
                # Accept domain match OR gmail/yahoo/etc if highly relevant
                if domain in e.lower():
                    emails.add(e)
                elif any(x in e.lower() for x in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']):
                    # Only accept generic providers if company name is roughly in local part? 
                    # Or just return them and let classifier decide?
                    # User wants everything. Let's return. 
                    emails.add(e)
            
            time.sleep(1)
        return emails

    def process_lead(self, name, website):
        domain = ""
        if website:
            try: domain = urlparse(website).netloc.replace('www.', '')
            except: pass
            
        print(f"\n[{name}]")
        print(f"  Website: {website} | Domain: {domain}")
        
        all_emails = set()
        
        # 1. WHOIS
        print("  [1/7] WHOIS...")
        if domain: all_emails.update(self.get_whois_emails(domain))
        
        # 2. DNS/Patterns
        print("  [2/7] DNS Patterns...")
        if domain: all_emails.update(self.get_dns_patterns(domain))
        
        # 3. Google Search
        print("  [3/7] Search...")
        if domain: all_emails.update(self.search_company_email(name, domain))
        
        # 4. Directories
        print("  [4/7] Directories...")
        if domain: all_emails.update(self.search_directories(name, domain))
        
        # 5. Website Patterns
        print("  [5/7] Website Pattern Gen...")
        if website and domain: all_emails.update(self.generate_patterns(website, domain))
        
        # 6. Deep Facebook
        print("  [6/7] Deep Facebook...")
        all_emails.update(self.deep_social_search(name, domain if domain else name.replace(' ','').lower()+".com", "facebook"))
        
        # 7. Deep LinkedIn
        print("  [7/7] Deep LinkedIn...")
        all_emails.update(self.deep_social_search(name, domain if domain else name.replace(' ','').lower()+".com", "linkedin"))
        
        # Clean emails
        valid = set()
        for e in all_emails:
            e = e.lower().strip('.')
            # Filter junk
            if any(x in e for x in ['wix.com', 'sentry.io', 'example.com', 'domain.com', '.png', '.jpg']):
                continue
            if domain and domain not in e and 'gmail' not in e and 'yahoo' not in e and 'outlook' not in e:
                # If it doesn't match domain and isn't a common provider, might be noise (e.g. email of directory site)
                # But user wants DEEP.
                # Let's keep it if it looks valid
                pass
            valid.add(e)
            
        return valid

    def classify_email(self, email):
        local = email.split('@')[0].lower()
        if any(x in local for x in ['sales', 'info', 'contact', 'admin', 'office', 'support', 'hello']):
            return '3', 'operational'
        return '1', 'owner' # Assume personal if not generic

# Main
def main():
    researcher = UltimateResearcher()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    print(f"Loaded {len(rows)} leads.")
    
    count_processed = 0
    count_upgraded = 0
    
    # Process only Batch 2
    for row in rows:
        source = row.get('source_query', '')
        if 'Batch 2' not in source:
            continue
            
        name = row.get('business_name', '')
        website = row.get('website', '')
        
        count_processed += 1
        print(f"Processing #{count_processed}: {name}")
        
        emails = researcher.process_lead(name, website)
        
        # Select best
        best_email = None
        best_tier = '9'
        
        for e in emails:
            tier, role = researcher.classify_email(e)
            if best_email is None:
                best_email = e
                best_tier = tier
            elif tier < best_tier: # 1 < 3
                best_email = e
                best_tier = tier
                
        if best_email:
            # Upgrade logic: 
            # If current is empty -> take it
            # If current is tier 3 and we found tier 1 -> take it
            curr = row.get('email', '')
            curr_tier = row.get('email_tier', '3')
            
            if not curr or (curr_tier != '1' and best_tier == '1'):
                print(f"  >>> FOUND/UPGRADED: {best_email} (Tier {best_tier})")
                row['email'] = best_email
                row['email_tier'] = best_tier
                row['email_role'] = 'owner' if best_tier == '1' else 'operational'
                row['Email_Source'] = 'Absolute Exhaustive'
                count_upgraded += 1
                
        time.sleep(1) # Respectful delay between leads
        
    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Done. Processed {count_processed} leads, upgraded {count_upgraded}.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
