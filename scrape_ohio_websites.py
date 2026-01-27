import csv
import re
import sys
import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher

logging.basicConfig(level=logging.INFO, format='%(message)s')

def scrape_website_simple(url):
    """Simple website scraper to find emails"""
    emails = set()
    
    try:
        # Try homepage
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        html = response.text
        
        # Find emails with regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, html, re.IGNORECASE)
        emails.update(found_emails)
        
        # Try /contact page
        contact_url = urljoin(url, '/contact')
        response = requests.get(contact_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        found_emails = re.findall(email_pattern, response.text, re.IGNORECASE)
        emails.update(found_emails)
        
    except:
        pass
    
    return emails

input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

enricher = LeadEnricher(config={"keyword": "hvac"})

# Load leads
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

logging.info(f"Direct Website Scraping for Ohio Leads")
logging.info(f"=" * 60)

found_count = 0
processed = 0

for i, row in enumerate(rows, 1):
    name = row.get('business_name', '')
    website = row.get('website', '')
    existing_email = row.get('email', '')
    
    # Only process leads without emails
    if existing_email or not website:
        continue
    
    processed += 1
    logging.info(f"[{processed}/27] Scraping: {name[:50]}")
    
    try:
        # Extract domain
        from urllib.parse import urlparse
        domain = urlparse(website).netloc.replace('www.', '')
        
        # Scrape for emails
        emails = scrape_website_simple(website)
        
        if emails:
            # Filter and prioritize
            valid_emails = []
            for email in emails:
                email_lower = email.lower()
                # Skip junk
                if any(bad in email_lower for bad in ['example.com', 'domain.com', 'noreply', 'donotreply']):
                    continue
                # Validate
                if enricher.is_valid_lead(email, domain):
                    valid_emails.append(email)
            
            if valid_emails:
                # Use prioritize_contacts to get best email
                email_set = set(valid_emails)
                best_email, _, email_role = enricher.prioritize_contacts(email_set, set(), domain)
                
                if best_email:
                    tier_string, role = enricher.categorize_email_role(best_email)
                    row['email'] = best_email
                    row['Email_Source'] = tier_string
                    row['email_role'] = role
                    tier_num = '1' if role == 'owner' else '2' if role == 'generic' else '3'
                    row['email_tier'] = tier_num
                    
                    logging.info(f"   Found: {best_email} ({tier_string})")
                    found_count += 1
                else:
                    logging.info(f"   No valid email after filtering")
        else:
            logging.info(f"   No emails found")
            
    except Exception as e:
        logging.info(f"   Error: {str(e)[:30]}")

# Save results
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

logging.info(f"\n" + "=" * 60)
logging.info(f"Direct Scraping Complete!")
logging.info(f"Processed: {processed} websites")
logging.info(f"Found: {found_count} new emails")
logging.info(f"Success Rate: {(found_count/processed*100):.1f}%" if processed > 0 else "N/A")
logging.info(f"\nSaved to: {output_file}")
