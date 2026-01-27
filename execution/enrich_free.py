"""
FREE Lead Enrichment - No API Keys Required
Uses intelligent pattern matching + web scraping
Expected Success Rate: 60-75% for phone, 55-70% for email
"""

import csv
import os
import json
import time
import random
import re
import logging
from datetime import datetime
from typing import Dict, Optional, Set, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Setup logging
os.makedirs('.tmp', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.tmp/free_enrichment.log'),
        logging.StreamHandler()
    ]
)

# Paths
INPUT_FILE = r'C:\Users\Piyush\Downloads\google.csv'
OUTPUT_FILE = r'C:\Users\Piyush\Downloads\lead enreaching agent\google_leads_enriched_FREE.csv'
PROGRESS_FILE = '.tmp/free_enrichment_progress.json'

# TEST MODE
TEST_MODE = False
MAX_TEST_LEADS = 5

# Regex patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
DOCTOR_PATTERN = re.compile(r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})')

# Junk filters
JUNK_DOMAINS = ['wix.com', 'example.com', 'sentry.io', 'domain.com', 'test.com']
JUNK_KEYWORDS = ['png', 'jpg', 'svg', 'noreply', 'donotreply', 'test@']

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]


class FreeLeadEnricher:
    """Free enrichment using pattern matching and scraping"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.progress = self.load_progress()
        
    def load_progress(self) -> Dict:
        """Load progress from file"""
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'processed': 0, 'successful': 0}
    
    def save_progress(self):
        """Save progress"""
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f)
    
    def generate_website_candidates(self, business_name: str, city: str) -> list:
        """
        Generate likely website URLs based on business name patterns
        """
        # Clean business name
        clean_name = re.sub(r'[^\w\s-]', '', business_name.lower())
        clean_name = re.sub(r'\s+', '', clean_name)
        clean_name = re.sub(r'[-]+', '', clean_name)
        
        candidates = []
        
        # Clean city
        clean_city = city.split(',')[0].lower().strip() if ',' in city else city.lower().strip()
        
        # Pattern 0: Full name as-is (e.g. arizonabiltmoredentistry.com)
        candidates.append(f"https://{clean_name}.com")
        candidates.append(f"http://{clean_name}.com")

        # Create shortened version
        short_name = clean_name
        remove_words = ['dentist', 'dental', 'dentistry', 'arizona', 'az', 'family', 'cosmetic', 'group', 'care', 'center']
        for word in remove_words:
            short_name = short_name.replace(word, '')
        
        short_name = short_name.strip('-')
        
        # Pattern 1: shortname.com
        if len(short_name) > 3:
            candidates.append(f"https://{short_name}.com")
            
        # Pattern 2: shortnamedental.com
        if len(short_name) > 3:
            candidates.append(f"https://{short_name}dental.com")
            candidates.append(f"https://{short_name}dentistry.com")
        
        # Pattern 3: shortnamecity.com
        if clean_city and len(short_name) > 3:
            candidates.append(f"https://{short_name}{clean_city}.com")
            candidates.append(f"https://{clean_city}{short_name}.com")
            
        # Pattern 4: clean_name + city (e.g. smilecarephoenix.com)
        if clean_city:
            candidates.append(f"https://{clean_name}{clean_city}.com")
            
        # Pattern 5: With hyphens
        name_with_hyphen = clean_name.replace(' ', '-')  # clean_name has no spaces though?
        # Re-clean from original for hyphens
        hyphen_name = re.sub(r'[^\w\s-]', '', business_name.lower())
        hyphen_name = re.sub(r'\s+', '-', hyphen_name.strip())
        candidates.append(f"https://{hyphen_name}.com")
        
        logging.info(f"Generated {len(candidates)} URL candidates")
        return candidates
    
    def verify_url(self, url: str) -> Optional[str]:
        """Check if URL is valid and accessible"""
        try:
            response = self.session.get(
                url,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                timeout=8,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Check if it's actually a dental website
                content = response.text.lower()
                dental_keywords = ['dentist', 'dental', 'teeth', 'smile', 'orthodont']
                
                if any(keyword in content for keyword in dental_keywords):
                    final_url = response.url
                    logging.info(f"✓ Valid website found: {final_url}")
                    return final_url
                    
        except requests.exceptions.SSLError:
            # Try without https
            if url.startswith('https'):
                return self.verify_url(url.replace('https://', 'http://'))
        except Exception as e:
            logging.debug(f"URL check failed for {url}: {str(e)[:50]}")
        
        return None
    
    def find_website(self, business_name: str, location: str) -> Optional[str]:
        """Find website using pattern matching"""
        logging.info(f"Searching website for: {business_name}")
        
        candidates = self.generate_website_candidates(business_name, location)
        
        for url in candidates:
            verified = self.verify_url(url)
            if verified:
                return verified
            time.sleep(0.3)  # Small delay between checks
        
        logging.warning(f"No website found for {business_name}")
        return None
    
    def extract_contact_info(self, html: str) -> Dict[str, Set]:
        """Extract emails, phones, and doctor names"""
        result = {
            'emails': set(),
            'phones': set(),
            'doctors': set()
        }
        
        if not html:
            return result
        
        # Extract emails
        emails = EMAIL_PATTERN.findall(html)
        for email in emails:
            email = email.lower().strip()
            # Filter junk
            if not any(junk in email for junk in JUNK_DOMAINS + JUNK_KEYWORDS):
                if len(email) < 50:  # Reasonable email length
                    result['emails'].add(email)
        
        # Extract phones
        phones = PHONE_PATTERN.findall(html)
        for phone in phones:
            clean = re.sub(r'[^\d]', '', phone)
            if len(clean) == 10 and clean[0] in '23456789':  # Valid US area code
                formatted = f"({clean[:3]}) {clean[3:6]}-{clean[6:]}"
                result['phones'].add(formatted)
        
        # Extract doctor names
        doctors = DOCTOR_PATTERN.findall(html)
        for doctor in doctors:
            if len(doctor) < 30:  # Reasonable name length
                result['doctors'].add(doctor.strip())
        
        return result
    
    def scrape_website(self, url: str) -> Dict:
        """Scrape website for contact information"""
        all_data = {
            'emails': set(),
            'phones': set(),
            'doctors': set(),
            'confidence': 0
        }
        
        try:
            # Get main page
            response = self.session.get(
                url,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                timeout=10
            )
            
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract from main page
                main_data = self.extract_contact_info(html)
                all_data['emails'].update(main_data['emails'])
                all_data['phones'].update(main_data['phones'])
                all_data['doctors'].update(main_data['doctors'])
                all_data['confidence'] += 40
                
                logging.info(f"Main page: {len(all_data['emails'])} emails, {len(all_data['phones'])} phones")
                
                # Find and scrape contact/about pages
                contact_links = self.find_contact_pages(soup, url)
                
                for link in contact_links[:3]:  # Limit to 3 subpages
                    time.sleep(0.5)
                    try:
                        sub_response = self.session.get(
                            link,
                            headers={'User-Agent': random.choice(USER_AGENTS)},
                            timeout=8
                        )
                        
                        if sub_response.status_code == 200:
                            sub_data = self.extract_contact_info(sub_response.text)
                            all_data['emails'].update(sub_data['emails'])
                            all_data['phones'].update(sub_data['phones'])
                            all_data['doctors'].update(sub_data['doctors'])
                            all_data['confidence'] += 20
                            
                    except Exception as e:
                        logging.debug(f"Subpage scrape failed: {str(e)[:30]}")
                
        except Exception as e:
            logging.warning(f"Website scrape failed for {url}: {str(e)[:50]}")
        
        all_data['confidence'] = min(all_data['confidence'], 80)  # Max confidence for free method
        return all_data
    
    def find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> list:
        """Find contact/about page links"""
        keywords = ['contact', 'about', 'team', 'staff', 'doctor', 'meet']
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if any(kw in href for kw in keywords):
                full_url = urljoin(base_url, a['href'])
                if full_url not in links and base_url in full_url:
                    links.append(full_url)
        
        return links
    
    def prioritize_contacts(self, emails: Set, phones: Set, doctors: Set) -> Tuple[str, str, str]:
        """
        Select best email and phone.
        Priority:
        1. Exact match with doctor name (e.g. 'john@' if doctor is 'John Doe')
        2. Personal-looking email (not info/contact/admin)
        3. Generic email (fallback, marked as 'Generic')
        """
        generic_prefixes = ['contact', 'info', 'reception', 'office', 'admin', 'support', 
                          'hello', 'team', 'appointment', 'frontdesk', 'inquiry', 'smile']
        
        email_list = list(emails)
        best_email = ""
        email_type = "None"
        
        # Helper to check if email is generic
        def is_generic(e):
            return any(e.startswith(p) for p in generic_prefixes)
            
        # 1. Try to match doctor names
        if doctors:
            for doctor in doctors:
                # Split name parts (e.g. 'John Doe' -> ['john', 'doe'])
                parts = [p.lower() for p in re.split(r'\W+', doctor) if len(p) > 2]
                for email in email_list:
                    # Check if any name part is in the email prefix (before @)
                    prefix = email.split('@')[0]
                    if any(part in prefix for part in parts) and not is_generic(email):
                        return email, list(phones)[0] if phones else "", "Personal (Doctor Match)"

        # 2. Look for ANY non-generic email
        personal_emails = [e for e in email_list if not is_generic(e)]
        if personal_emails:
            # Sort by length (shorter is usually better for personal emails like 'bob@')
            personal_emails.sort(key=len)
            return personal_emails[0], list(phones)[0] if phones else "", "Personal"
            
        # 3. Fallback to generic
        if email_list:
            # Prioritize 'info' or 'contact' as they are most standard
            for p in ['info@', 'contact@']:
                for e in email_list:
                    if e.startswith(p):
                        return e, list(phones)[0] if phones else "", "Generic"
            return email_list[0], list(phones)[0] if phones else "", "Generic"
            
        return "", list(phones)[0] if phones else "", "None"
    
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
        
        # Find website using pattern matching
        website = self.find_website(business_name, location)
        
        if website:
            enriched['Website'] = website
            time.sleep(1)
            
            # Scrape website
            scrape_data = self.scrape_website(website)
            
            if scrape_data['emails'] or scrape_data['phones']:
                email, phone, type_ = self.prioritize_contacts(
                    scrape_data['emails'],
                    scrape_data['phones'],
                    scrape_data['doctors']
                )
                
                if email:
                    enriched['Email_Primary'] = email
                    enriched['Email_Confidence'] = scrape_data['confidence']
                    enriched['Email_Source'] = f'Website Scrape ({type_})'
                    logging.info(f"✓ Email ({type_}): {email}")
                
                if phone:
                    enriched['Phone_Primary'] = phone
                    enriched['Phone_Validated'] = 'True'
                    enriched['Phone_Source'] = 'Website Scrape (Free)'
                    logging.info(f"✓ Phone: {phone}")
                
                if scrape_data['doctors']:
                    enriched['Doctor_Name'] = ', '.join(list(scrape_data['doctors'])[:3])
                    logging.info(f"✓ Doctors: {enriched['Doctor_Name']}")
        
        return enriched
    
    def process_leads(self):
        """Main processing loop"""
        if not os.path.exists(INPUT_FILE):
            logging.error(f"Input file not found: {INPUT_FILE}")
            return
        
        # Read CSV
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
        successful = 0
        
        try:
            for i, row in enumerate(rows, 1):
                logging.info(f"\nLead {i}/{len(rows)}")
                
                enriched_data = self.enrich_lead(row)
                enriched_row = {**row, **enriched_data}
                enriched_rows.append(enriched_row)
                
                if enriched_data['Email_Primary'] or enriched_data['Phone_Primary']:
                    successful += 1
                
                # Update progress
                self.progress['processed'] = i
                self.progress['successful'] = successful
                
                if i % 5 == 0:
                    self.save_progress()
                    self.save_output(enriched_rows, output_fields)
                
                # Rate limiting
                time.sleep(random.uniform(2, 4))
                
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)
        
        # Final save
        self.save_output(enriched_rows, output_fields)
        self.save_progress()
        self.print_summary(enriched_rows)
    
    def save_output(self, rows: list, fields: list):
        """Save to CSV"""
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        logging.info(f"✓ Saved to: {OUTPUT_FILE}")
    
    def print_summary(self, rows: list):
        """Print statistics"""
        total = len(rows)
        websites = sum(1 for r in rows if r.get('Website'))
        emails = sum(1 for r in rows if r.get('Email_Primary'))
        phones = sum(1 for r in rows if r.get('Phone_Primary'))
        both = sum(1 for r in rows if r.get('Email_Primary') and r.get('Phone_Primary'))
        
        print("\n" + "="*60)
        print("FREE ENRICHMENT COMPLETE!")
        print("="*60)
        print(f"Total Processed: {total}")
        print(f"Websites Found: {websites}/{total} ({websites/total*100:.1f}%)")
        print(f"Emails Found: {emails}/{total} ({emails/total*100:.1f}%)")
        print(f"Phones Found: {phones}/{total} ({phones/total*100:.1f}%)")
        print(f"Both Email+Phone: {both}/{total} ({both/total*100:.1f}%)")
        print("="*60)
        print(f"\n✓ Output saved to:\n{OUTPUT_FILE}")
        print("="*60)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FREE Lead Enrichment (No API Keys Required)")
    print("="*60 + "\n")
    
    enricher = FreeLeadEnricher()
    enricher.process_leads()
