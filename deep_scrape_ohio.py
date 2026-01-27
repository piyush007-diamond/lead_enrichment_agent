import csv
import re
import requests
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def deep_scrape_for_emails(website, business_name):
    """
    Aggressive multi-page scraping for emails
    Tries: homepage,/contact, /about, /team, /contact-us
    """
    emails = set()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    # Pages to try
    pages = [
        '',  # Homepage
        '/contact',
        '/contact-us',
        '/about',
        '/about-us',
        '/team',
        '/our-team',
        '/company'
    ]
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    for page in pages:
        try:
            url = website.rstrip('/') + page
            response = session.get(url, timeout=10)
            
            # Extract visible text
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # Find all emails
            found = re.findall(email_pattern, text, re.IGNORECASE)
            emails.update(found)
            
        except:
            continue
    
    # Filter out junk
    valid_emails = set()
    for email in emails:
        email_lower = email.lower()
        
        # Skip examples and noreply
        if any(bad in email_lower for bad in ['example.com', 'domain.com', 'noreply', 
                                                'donotreply', 'sampleemail', 'youremail',
                                                'test@', '@test']):
            continue
        
        # Must have proper TLD
        if not re.search(r'\.(com|net|org|us|co|io)$', email_lower):
            continue
            
        valid_emails.add(email)
    
    return valid_emails

# Main execution
input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

logging.info("="*60)
logging.info("Deep Multi-Page Scraping for 21 Leads")
logging.info("="*60)

found_count = 0
processed = 0

for i, row in enumerate(rows, 1):
    if row.get('email') or not row.get('website'):
        continue
    
    processed += 1
    name = row.get('business_name', '')
    website = row.get('website', '')
    
    logging.info(f"\n[{processed}/21] {name[:50]}")
    logging.info(f"   Website: {website}")
    
    # Deep scrape
    emails = deep_scrape_for_emails(website, name)
    
    if emails:
        # Prioritize by role
        for email in emails:
            local_part = email.split('@')[0].lower()
            
            # Check for owner/personal names (not generic)
            generic_keywords = ['info', 'contact', 'hello', 'support', 'service', 
                               'admin', 'sales', 'customerservice', 'help']
            
            if not any(k in local_part for k in generic_keywords):
                # Looks like a personal email
                row['email'] = email
                row['email_role'] = 'owner'
                row['email_tier'] = '1'
                row['Email_Source'] = 'Deep Scrape: Tier 1 (Decision Maker)'
                logging.info(f"   => FOUND (Personal): {email}")
                found_count += 1
                break
        
        # If no personal email, take generic
        if not row.get('email'):
            best = list(emails)[0]
            row['email'] = best
            row['email_role'] = 'generic'
            row['email_tier'] = '2'
            row['Email_Source'] = 'Deep Scrape: Tier 2 (Generic)'
            logging.info(f"   => FOUND (Generic): {best}")
            found_count += 1
    else:
        logging.info(f"   => NO EMAILS FOUND")
    
    time.sleep(1)  # Rate limiting

# Save
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

logging.info(f"\n{'='*60}")
logging.info(f"Deep Scraping Complete")
logging.info(f"Processed: {processed} websites")
logging.info(f"Found: {found_count} new emails")
logging.info(f"Success Rate: {(found_count/processed*100):.1f}%" if processed > 0 else "N/A")
logging.info(f"\nSaved to: {output_file}")
