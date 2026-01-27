"""
Google Places API Enhanced Lead Enrichment
Uses Google Places API for maximum accuracy + pattern matching fallback
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
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.tmp/google_places_enrichment.log'),
        logging.StreamHandler()
    ]
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT_FILE = r'C:\Users\Piyush\Downloads\google.csv'
OUTPUT_FILE = os.path.join(BASE_DIR, 'google_leads_enriched_FINAL.csv')

# API Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
PLACES_API_URL = "https://maps.googleapis.com/maps/api/place"

# TEST MODE
TEST_MODE = True  # Change to False to process all leads
MAX_TEST_LEADS = 5

# Regex patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
DOCTOR_PATTERN = re.compile(r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)')

# Junk filters
JUNK_DOMAINS = ['wix.com', 'example.com', 'sentry.io', 'domain.com']
JUNK_KEYWORDS = ['png', 'jpg', 'svg', 'noreply']

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
]


class GooglePlacesEnricher:
    """Enhanced enricher using Google Places API"""
    
    def __init__(self):
        self.session = requests.Session()
        self.api_key = GOOGLE_API_KEY
        os.makedirs('.tmp', exist_ok=True)
        
        if not self.api_key:
            logging.warning("No Google API key found! Using fallback methods only.")
        else:
            logging.info("✓ Google Places API key loaded")
            self.test_api_key()
    
    def test_api_key(self):
        """Test if API key works"""
        try:
            test_url = f"{PLACES_API_URL}/textsearch/json"
            params = {
                'query': 'dentist Phoenix Arizona',
                'key': self.api_key
            }
            response = requests.get(test_url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == 'OK':
                logging.info("✓ Google Places API key is VALID and working!")
                return True
            elif data.get('status') == 'REQUEST_DENIED':
                logging.error(f"✗ API Key Error: {data.get('error_message', 'Unknown error')}")
                logging.error("Make sure Places API is enabled in Google Cloud Console")
                return False
            else:
                logging.warning(f"API Status: {data.get('status')}")
                return False
        except Exception as e:
            logging.error(f"API test failed: {e}")
            return False
    
    def search_with_google_places(self, business_name: str, location: str) -> Optional[Dict]:
        """
        Use Google Places API to find business details
        """
        if not self.api_key:
            return None
            
        try:
            # Text Search
            search_url = f"{PLACES_API_URL}/textsearch/json"
            query = f"{business_name} dentist {location}"
            
            params = {
                'query': query,
                'key': self.api_key
            }
            
            logging.info(f"Google Places search: {query}")
            response = requests.get(search_url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') != 'OK' or not data.get('results'):
                logging.warning(f"No Google Places results for: {business_name}")
                return None
            
            # Get first result (usually the most relevant)
            place = data['results'][0]
            place_id = place.get('place_id')
            
            if not place_id:
                return None
            
            # Get Place Details for phone, website, etc.
            time.sleep(0.5)  # Rate limiting
            details = self.get_place_details(place_id)
            
            return details
            
        except Exception as e:
            logging.error(f"Google Places API error: {e}")
            return None
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed information about a place"""
        try:
            details_url = f"{PLACES_API_URL}/details/json"
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_phone_number,website,international_phone_number',
                'key': self.api_key
            }
            
            response = requests.get(details_url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') == 'OK':
                result = data.get('result', {})
                logging.info(f"✓ Got details: Phone={result.get('formatted_phone_number')}, Website={result.get('website')}")
                return result
                
        except Exception as e:
            logging.error(f"Failed to get place details: {e}")
        
        return None
    
    def scrape_website(self, url: str) -> Dict:
        """Scrape website for additional contact info"""
        result = {
            'emails': set(),
            'phones': set(),
            'doctors': set(),
        }
        
        try:
            logging.info(f"Scraping website: {url}")
            response = self.session.get(
                url,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                timeout=10
            )
            
            if response.status_code == 200:
                html = response.text
                
                # Extract emails
                emails = EMAIL_PATTERN.findall(html)
                for email in emails:
                    email = email.lower().strip()
                    if not any(j in email for j in JUNK_DOMAINS + JUNK_KEYWORDS):
                        result['emails'].add(email)
                
                # Extract phones
                phones = PHONE_PATTERN.findall(html)
                for phone in phones:
                    clean = re.sub(r'[^\d]', '', phone)
                    if len(clean) == 10:
                        formatted = f"({clean[:3]}) {clean[3:6]}-{clean[6:]}"
                        result['phones'].add(formatted)
                
                # Extract doctor names
                doctors = DOCTOR_PATTERN.findall(html)
                result['doctors'].update(doctors)
                
                logging.info(f"Scraped: {len(result['emails'])} emails, {len(result['phones'])} phones")
                
        except Exception as e:
            logging.warning(f"Scraping failed for {url}: {e}")
        
        return result
    
    def prioritize_email(self, emails: set) -> str:
        """Select best email"""
        if not emails:
            return ""
        
        priority = ['contact@', 'info@', 'reception@', 'office@']
        emails_list = list(emails)
        
        for p in priority:
            for email in emails_list:
                if email.startswith(p):
                    return email
        
        return emails_list[0]
    
    def enrich_lead(self, row: Dict) -> Dict:
        """Main enrichment function"""
        business_name = row.get('OSrXXb', '')
        location = row.get('rllt__details 2', '')
        
        logging.info("="*60)
        logging.info(f"Processing: {business_name} ({location})")
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
        
        # Strategy 1: Google Places API
        if self.api_key:
            places_data = self.search_with_google_places(business_name, location)
            
            if places_data:
                # Get phone from Google
                phone = places_data.get('formatted_phone_number') or places_data.get('international_phone_number')
                if phone:
                    enriched['Phone_Primary'] = phone
                    enriched['Phone_Validated'] = 'True'
                    enriched['Phone_Source'] = 'Google Places API'
                    enriched['Email_Confidence'] = 90
                    logging.info(f"✓ Phone from Google: {phone}")
                
                # Get website from Google
                website = places_data.get('website')
                if website:
                    enriched['Website'] = website
                    logging.info(f"✓ Website from Google: {website}")
                    
                    # Strategy 2: Scrape website for email
                    time.sleep(1)
                    scrape_result = self.scrape_website(website)
                    
                    if scrape_result['emails']:
                        email = self.prioritize_email(scrape_result['emails'])
                        enriched['Email_Primary'] = email
                        enriched['Email_Source'] = 'Website Scrape'
                        enriched['Email_Confidence'] = 85
                        logging.info(f"✓ Email from website: {email}")
                    
                    if scrape_result['doctors']:
                        enriched['Doctor_Name'] = ', '.join(list(scrape_result['doctors'])[:3])
                        logging.info(f"✓ Doctors: {enriched['Doctor_Name']}")
        
        return enriched
    
    def process_leads(self):
        """Main processing function"""
        if not os.path.exists(INPUT_FILE):
            logging.error(f"Input file not found: {INPUT_FILE}")
            return
        
        # Read input
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            rows = list(reader)
        
        logging.info(f"Loaded {len(rows)} leads")
        
        if TEST_MODE:
            rows = rows[:MAX_TEST_LEADS]
            logging.info(f"TEST MODE: Processing {MAX_TEST_LEADS} leads")
        
        # Output fields
        output_fields = fieldnames + [
            'Website', 'Email_Primary', 'Email_Confidence', 'Email_Source',
            'Phone_Primary', 'Phone_Validated', 'Phone_Source',
            'Doctor_Name', 'Last_Updated'
        ]
        
        enriched_rows = []
        
        try:
            for i, row in enumerate(rows, 1):
                logging.info(f"\n{'='*60}")
                logging.info(f"Lead {i}/{len(rows)}")
                logging.info(f"{'='*60}")
                
                enriched_data = self.enrich_lead(row)
                enriched_row = {**row, **enriched_data}
                enriched_rows.append(enriched_row)
                
                # Rate limiting
                if i < len(rows):
                    time.sleep(random.uniform(1, 2))
                
        except KeyboardInterrupt:
            logging.info("Process interrupted")
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)
        
        # Save results
        self.save_output(enriched_rows, output_fields)
        
        # Print summary
        self.print_summary(enriched_rows)
    
    def save_output(self, rows: list, fields: list):
        """Save to CSV"""
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        logging.info(f"✓ Saved to: {OUTPUT_FILE}")
    
    def print_summary(self, rows: list):
        """Print enrichment statistics"""
        total = len(rows)
        websites = sum(1 for r in rows if r.get('Website'))
        emails = sum(1 for r in rows if r.get('Email_Primary'))
        phones = sum(1 for r in rows if r.get('Phone_Primary'))
        
        logging.info("\n" + "="*60)
        logging.info("ENRICHMENT COMPLETE!")
        logging.info("="*60)
        logging.info(f"Total Processed: {total}")
        logging.info(f"Websites Found: {websites}/{total} ({websites/total*100:.1f}%)")
        logging.info(f"Emails Found: {emails}/{total} ({emails/total*100:.1f}%)")
        logging.info(f"Phones Found: {phones}/{total} ({phones/total*100:.1f}%)")
        logging.info(f"Both Email+Phone: {sum(1 for r in rows if r.get('Email_Primary') and r.get('Phone_Primary'))}/{total}")
        logging.info("="*60)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Google Places API Lead Enrichment")
    print("="*60 + "\n")
    
    enricher = GooglePlacesEnricher()
    enricher.process_leads()
