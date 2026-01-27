"""
TEST VERSION - Process only first 5 leads
Enhanced Lead Enrichment Script for Google Dentist Leads
"""

import csv
import os
import json
import time
import random
import re
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.tmp/test_enrichment.log'),
        logging.StreamHandler()
    ]
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT_FILE = r'C:\Users\Piyush\Downloads\google.csv'
OUTPUT_FILE = os.path.join(BASE_DIR, 'test_enriched_5_leads.csv')

# TEST MODE - Only process 5 leads
TEST_MODE = True
MAX_TEST_LEADS = 5

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Regex patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
DOCTOR_PATTERN = re.compile(r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)')

# Junk email filters
JUNK_DOMAINS = ['wix.com', 'example.com', 'sentry.io', 'domain.com', 'email.com']
JUNK_KEYWORDS = ['png', 'jpg', 'svg', 'noreply', 'donotreply']


class LeadEnricher:
    """Main class for enriching dental practice leads"""
    
    def __init__(self):
        self.session = requests.Session()
        os.makedirs('.tmp', exist_ok=True)
        
    def get_random_headers(self) -> Dict:
        """Generate random headers"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def rate_limit_delay(self):
        """Random delay to avoid rate limiting"""
        delay = random.uniform(2, 4)
        logging.info(f"Rate limiting delay: {delay:.2f}s")
        time.sleep(delay)
    
    def search_website(self, business_name: str, location: str) -> Optional[str]:
        """
        Strategy 1: Search for official website using DuckDuckGo
        """
        try:
            from duckduckgo_search import DDGS
            
            query = f'"{business_name}" "{location}" dentist'
            logging.info(f"Searching for: {query}")
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            
            logging.info(f"Found {len(results)} search results")
                
            for result in results:
                url = result.get('href', '')
                logging.info(f"Checking URL: {url}")
                
                # Filter out directories
                if any(site in url.lower() for site in ['yelp', 'facebook', 'healthgrades', 'zocdoc', 'yellowpages', 'linkedin']):
                    logging.info(f"Skipping directory site: {url}")
                    continue
                
                # Verify it's a real website
                if self.verify_website(url):
                    logging.info(f"✓ Found valid website: {url}")
                    return url
                    
        except Exception as e:
            logging.error(f"Website search failed for {business_name}: {e}")
            
        return None
    
    def verify_website(self, url: str) -> bool:
        """Verify URL is accessible and valid"""
        try:
            response = self.session.get(
                url, 
                headers=self.get_random_headers(), 
                timeout=10,
                allow_redirects=True
            )
            logging.info(f"Website status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logging.warning(f"Website verification failed: {e}")
            return False
    
    def scrape_website(self, url: str) -> Dict[str, any]:
        """
        Strategy 1: Extract contact info from website
        """
        result = {
            'emails': set(),
            'phones': set(),
            'doctors': set(),
            'confidence': 0
        }
        
        try:
            # Scrape main page
            logging.info(f"Scraping main page: {url}")
            html = self.get_page_content(url)
            if html:
                self.extract_contact_info(html, result)
                result['confidence'] += 30
                logging.info(f"Main page: Found {len(result['emails'])} emails, {len(result['phones'])} phones")
                
            # Try to find and scrape contact/about pages
            contact_urls = self.find_contact_pages(url, html)
            logging.info(f"Found {len(contact_urls)} contact pages")
            
            for contact_url in contact_urls[:2]:  # Limit to 2 subpages for test
                self.rate_limit_delay()
                logging.info(f"Scraping subpage: {contact_url}")
                sub_html = self.get_page_content(contact_url)
                if sub_html:
                    self.extract_contact_info(sub_html, result)
                    result['confidence'] += 20
                    
        except Exception as e:
            logging.error(f"Scraping failed for {url}: {e}")
        
        # Cap confidence at 95
        result['confidence'] = min(result['confidence'], 95)
        logging.info(f"Final extraction: {len(result['emails'])} emails, {len(result['phones'])} phones, {len(result['doctors'])} doctors, confidence: {result['confidence']}")
        return result
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Fetch page HTML content"""
        try:
            response = self.session.get(
                url,
                headers=self.get_random_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logging.warning(f"Failed to fetch {url}: {e}")
        return None
    
    def find_contact_pages(self, base_url: str, html: str) -> list:
        """Find contact/about pages""" 
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        contact_urls = []
        
        keywords = ['contact', 'about', 'team', 'staff', 'doctors']
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(keyword in href for keyword in keywords):
                full_url = urljoin(base_url, link['href'])
                if full_url and full_url not in contact_urls:
                    contact_urls.append(full_url)
                    
        return contact_urls
    
    def extract_contact_info(self, html: str, result: Dict):
        """Extract emails, phones, and doctor names from HTML"""
        if not html:
            return
            
        # Extract emails
        emails = EMAIL_PATTERN.findall(html)
        for email in emails:
            email = email.lower().strip()
            # Filter junk
            if not any(junk in email for junk in JUNK_DOMAINS + JUNK_KEYWORDS):
                result['emails'].add(email)
        
        # Extract phones
        phones = PHONE_PATTERN.findall(html)
        for phone in phones:
            # Clean and validate
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) == 10:
                # Format as (XXX) XXX-XXXX
                formatted = f"({clean_phone[:3]}) {clean_phone[3:6]}-{clean_phone[6:]}"
                result['phones'].add(formatted)
        
        # Extract doctor names
        doctors = DOCTOR_PATTERN.findall(html)
        for doctor in doctors:
            result['doctors'].add(doctor.strip())
    
    def prioritize_contacts(self, emails: set, phones: set) -> Tuple[str, str]:
        """Select best email and phone from multiple options"""
        # Email priority: contact > info > appointments > others
        email_priority = ['contact@', 'info@', 'appointment', 'reception@', 'office@']
        
        best_email = ""
        if emails:
            emails_list = list(emails)
            for priority in email_priority:
                for email in emails_list:
                    if email.startswith(priority):
                        best_email = email
                        break
                if best_email:
                    break
            if not best_email:
                best_email = emails_list[0]
        
        # Phone: just take the first one
        best_phone = list(phones)[0] if phones else ""
        
        return best_email, best_phone
    
    def enrich_lead(self, row: Dict) -> Dict:
        """
        Main enrichment function for a single lead
        """
        business_name = row.get('OSrXXb', '')
        location = row.get('rllt__details 2', '')
        
        logging.info("="*60)
        logging.info(f"Processing: {business_name} - {location}")
        logging.info("="*60)
        
        enriched = {
            'Website': '',
            'Email_Primary': '',
            'Email_Confidence': 0,
            'Email_Source': '',
            'Phone_Primary': '',
            'Phone_Validated': 'False',
            'Phone_Source': '',
            'Doctor_Name': '',
            'Last_Updated': datetime.now().isoformat()
        }
        
        # Strategy 1: Website scraping
        website = self.search_website(business_name, location)
        if website:
            enriched['Website'] = website
            self.rate_limit_delay()
            
            scrape_result = self.scrape_website(website)
            
            if scrape_result['emails'] or scrape_result['phones']:
                email, phone = self.prioritize_contacts(
                    scrape_result['emails'],
                    scrape_result['phones']
                )
                
                if email:
                    enriched['Email_Primary'] = email
                    enriched['Email_Confidence'] = scrape_result['confidence']
                    enriched['Email_Source'] = 'Website Direct'
                    logging.info(f"✓ Email found: {email}")
                
                if phone:
                    enriched['Phone_Primary'] = phone
                    enriched['Phone_Validated'] = 'True'
                    enriched['Phone_Source'] = 'Website Direct'
                    logging.info(f"✓ Phone found: {phone}")
                
                if scrape_result['doctors']:
                    enriched['Doctor_Name'] = ', '.join(list(scrape_result['doctors'])[:3])
                    logging.info(f"✓ Doctors found: {enriched['Doctor_Name']}")
        else:
            logging.warning(f"No website found for {business_name}")
        
        return enriched
    
    def process_leads(self):
        """Main processing function - TEST MODE"""
        if not os.path.exists(INPUT_FILE):
            logging.error(f"Input file not found: {INPUT_FILE}")
            return
        
        # Read input
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        logging.info(f"Loaded {len(rows)} leads from file")
        
        if TEST_MODE:
            rows = rows[:MAX_TEST_LEADS]
            logging.info(f"TEST MODE: Processing only first {MAX_TEST_LEADS} leads")
        
        # Prepare output fieldnames
        output_fieldnames = list(fieldnames) + [
            'Website', 'Email_Primary', 'Email_Confidence', 'Email_Source',
            'Phone_Primary', 'Phone_Validated', 'Phone_Source',
            'Doctor_Name', 'Last_Updated'
        ]
        
        enriched_rows = []
        
        try:
            for i, row in enumerate(rows, 1):
                logging.info(f"\n{'='*60}")
                logging.info(f"Progress: {i}/{len(rows)}")
                logging.info(f"{'='*60}")
                
                # Enrich the lead
                enriched_data = self.enrich_lead(row)
                
                # Merge with original data
                enriched_row = {**row, **enriched_data}
                enriched_rows.append(enriched_row)
                
                # Rate limiting between leads
                if i < len(rows):
                    self.rate_limit_delay()
                
        except KeyboardInterrupt:
            logging.info("Process interrupted by user")
        except Exception as e:
            logging.error(f"Error during processing: {e}")
        
        # Save output
        self.save_output(enriched_rows, output_fieldnames)
        
        # Print summary
        logging.info("\n" + "="*60)
        logging.info("TEST ENRICHMENT COMPLETE!")
        logging.info("="*60)
        logging.info(f"Output saved to: {OUTPUT_FILE}")
        logging.info(f"Processed: {len(enriched_rows)} leads")
        
        # Calculate success rate
        emails_found = sum(1 for row in enriched_rows if row.get('Email_Primary'))
        phones_found = sum(1 for row in enriched_rows if row.get('Phone_Primary'))
        websites_found = sum(1 for row in enriched_rows if row.get('Website'))
        
        logging.info(f"\nResults:")
        logging.info(f"  Websites found: {websites_found}/{len(enriched_rows)} ({websites_found/len(enriched_rows)*100:.1f}%)")
        logging.info(f"  Emails found: {emails_found}/{len(enriched_rows)} ({emails_found/len(enriched_rows)*100:.1f}%)")
        logging.info(f"  Phones found: {phones_found}/{len(enriched_rows)} ({phones_found/len(enriched_rows)*100:.1f}%)")
        logging.info("="*60)
    
    def save_output(self, rows: list, fieldnames: list):
        """Save enriched data to CSV"""
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logging.info(f"Data saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TEST MODE: Google Leads Enrichment (First 5 Leads)")
    print("="*60 + "\n")
    
    enricher = LeadEnricher()
    enricher.process_leads()
