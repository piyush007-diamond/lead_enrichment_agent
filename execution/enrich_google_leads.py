"""
Enhanced Lead Enrichment Script for Google Leads
Multi-strategy approach with validation and quality scoring.
Supports multiple niches via configuration.
"""

import csv
import os
import json
import time
import random
import re
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, Set
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import dns.resolver
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('.tmp/enrichment_errors.log'),
        logging.StreamHandler()
    ]
)

# Default Paths (Fallback)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_INPUT_FILE = r'C:\Users\Piyush\Downloads\google.csv'
DEFAULT_OUTPUT_FILE = os.path.join(BASE_DIR, 'google_leads_enriched.csv')
PROGRESS_FILE = '.tmp/google_enrichment_progress.json'

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
]

# Regex patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b')
PHONE_PATTERN = re.compile(r'\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}')

# Junk email filters
JUNK_DOMAINS = ['wix.com', 'example.com', 'sentry.io', 'domain.com', 'email.com', 'sentry', 'wixpress', 'canadiantire']
JUNK_KEYWORDS = ['png', 'jpg', 'svg', 'noreply', 'donotreply']

# Blacklist for website search (Directories & Social Media)
BLACKLIST_DOMAINS = [
    'yelp', 'yellowpages', 'bbb', 'angie', 'homeadvisor', 'thumbtack', 'porch', 'houzz',
    'facebook', 'instagram', 'linkedin', 'twitter', 'tiktok', 'youtube', 'pinterest',
    'zhihu', 'quora', 'wikihow', 'wikipedia', 'google', 'bing', 'yahoo', 'mapquest',
    'support.google', 'accounts.google', 'whitepages', 'zoominfo', 'chamberofcommerce',
    'dandb', 'manta', 'cylex', 'hotfrog', 'superpages', 'merchantcircle', 'nextdoor',
    'forum', 'baidu', 'thomasnet', 'dictionary.cambridge', 'britannica', 'naver.com',
    'phoronix', 'marks.com', 'wise.com', 'sur.ly', 'list.ly', 'forbes.com', 'microsoft.com',
    'stackexchange', 'rentechdigital', 'expertise.com', 'networx.com', 'inven.ai',
    'servicetitan.com', 'merriam-webster.com', 'trane.com', 'carrier.com', 'lennox.com',
    'goodmanmfg.com', 'rheem.com', 'york.com', 'bryant.com', 'americanstandardair.com',
    'indiamart', 'visitarizona', 'delhi.gov'
]

# Business Ownership Gate Keywords (Reject if found in URL/Title)
NON_BUSINESS_KEYWORDS = [
    'directory', 'marketplace', 'blog', 'guide', 'list', 'powered-by', 'find-a-dealer',
    'licensing', 'dictionary', 'definitions', 'top-10', 'best-of', 'near-me',
    'dealer', 'find-a', 'top-', 'best-', 'listing', 'poweredby'
]

# Additional Domains to Block Hard (User Specified)
BLACKLIST_DOMAINS.extend([
    'indiamart', 'visitarizona', 'delhi.gov', 'jagranjosh', 'inven.ai', 'servicetitan'
])

# Email Hygiene: Junk Strings to HARD REJECT
EMAIL_JUNK_STRINGS = [
    "example", "mysite", "domain.com", "demolink", "bug-reporting", "sentry.io", 
    "noreply", "wix.com", "wordpress.com", "email.com", "test.com", "yoursite.",
    "u003e", "%20", ".png", ".jpg", ".js", ".css", "admin@yoursite"
]

# Keywords that indicate a generic email
GENERIC_EMAIL_PREFIXES = ['info', 'contact', 'admin', 'service', 'office', 'support', 'sales', 'hello', 'inquiry', 'help']

# Pattern to find owner/founder names on About/Team pages
# Matches: "Owner: John Smith", "Founder - Jane Doe", "CEO: John Doe", etc.
# More strict pattern requiring proper punctuation between title and name
OWNER_TITLE_PATTERN = re.compile(
    r'\b(?:owner|founder|president|ceo|principal|proprietor)\s*[:\-–]\s*([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2})\b',
    re.MULTILINE
)

# Alternative pattern for "John Smith, Owner" format
# Requires at least 3 chars per name part to avoid matching "is", "or", etc.
OWNER_AFTER_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2})\s*[,\-–]\s*(?:Owner|Founder|President|CEO|Principal|Proprietor)\b'
)

# Words that are NOT valid names (filter out false positives)
INVALID_NAME_WORDS = ['is', 'or', 'to', 'also', 'very', 'the', 'and', 'our', 'your', 'their', 'has', 'was', 'are']

# Known MX Providers for Intelligence
MX_PROVIDERS = {
    'google': 15,
    'googlemail': 15,
    'outlook': 15,
    'microsoft': 15,
    'protection.outlook': 15,
    'zoho': 10,
    'fastmail': 10,
    'proton': 10,
    'mimecast': 5,
    'pphosted': 5, # Proofpoint
    'sendgrid': -10,
    'mailgun': -10
}


class LeadEnricher:
    """Main class for enriching leads with configurable strategies."""
    
    def __init__(self, config: Dict = None, input_file: str = None, output_file: str = None):
        self.session = requests.Session()
        self.config = config or {}
        self.input_file = input_file or DEFAULT_INPUT_FILE
        self.output_file = output_file or DEFAULT_OUTPUT_FILE
        self.progress = self.load_progress()
        
        # dynamic search query customization
        self.keyword = self.config.get('keyword', 'dentist')
        
        # Default Columns
        self.cols = {
            'name': 'OSrXXb',
            'location': 'rllt__details 2',
            'rating': 'yi40Hd',
            'reviews': 'RDApEe',
            'services': 'BI0Dve'
        }
        # Override with config
        if 'columns' in self.config:
            self.cols.update(self.config['columns'])
            
        # Compile doctor/contact name pattern if provided
        self.contact_pattern = None
        pattern_str = self.config.get('contact_title_pattern')
        if pattern_str:
            try:
                self.contact_pattern = re.compile(pattern_str)
            except re.error:
                logging.warning(f"Invalid contact_title_pattern: {pattern_str}")
                
        os.makedirs('.tmp', exist_ok=True)
        
    def load_progress(self) -> Dict:
        """Load progress from previous run"""
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {'last_processed': 0, 'processed_names': []}
        return {'last_processed': 0, 'processed_names': []}
    
    def save_progress(self):
        """Save current progress"""
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f)
    
    def get_random_headers(self) -> Dict:
        """Generate random headers"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def rate_limit_delay(self):
        """Random delay to avoid rate limiting"""
        time.sleep(random.uniform(2, 5))
    
    def search_website(self, business_name: str, location: str) -> Optional[str]:
        """
        Strategy 1: Search for official website using DuckDuckGo
        """
        try:
            from duckduckgo_search import DDGS
            
            # Use configured keyword
            query = f'"{business_name}" "{location}" {self.keyword} official website -yelp -facebook -healthgrades'
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                
            for result in results:
                url = result.get('href', '')
                # Filter out directories and blacklist domains
                if any(site in url.lower() for site in BLACKLIST_DOMAINS):
                    logging.info(f"Filtered blacklisted URL: {url}")
                    continue
                
                # Verify it's a real website
                if self.verify_website(url):
                    logging.info(f"Found website: {url}")
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
            return response.status_code == 200
        except:
            return False
    
    def scrape_website(self, url: str) -> Dict[str, any]:
        """
        Strategy 1: Extract contact info from website
        """
        # Extract domain for email generation
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        
        result = {
            'emails': set(), # Set of (priority, email) tuples
            'phones': set(),
            'doctors': set(),
            'confidence': 0,
            'domain': domain  # For owner email pattern generation
        }
        
        try:
            # Scrape main page
            html = self.get_page_content(url)
            if html:
                self.extract_contact_info(html, result)
                result['confidence'] += 30
                
            # Try to find and scrape contact/about pages
            contact_urls = self.find_contact_pages(url, html)
            for contact_url in contact_urls[:3]:  # Limit to 3 subpages
                self.rate_limit_delay()
                sub_html = self.get_page_content(contact_url)
                if sub_html:
                    self.extract_contact_info(sub_html, result)
                    result['confidence'] += 20
                    
        except Exception as e:
            logging.error(f"Scraping failed for {url}: {e}")
        
        # Cap confidence at 95
        result['confidence'] = min(result['confidence'], 95)
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
        
        keywords = ['contact', 'about', 'team', 'staff', 'doctors', 'our-team', 'meet']
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(keyword in href for keyword in keywords):
                full_url = self.make_absolute_url(base_url, link['href'])
                if full_url and full_url not in contact_urls:
                    contact_urls.append(full_url)
                    
        return contact_urls
    
    def make_absolute_url(self, base_url: str, href: str) -> Optional[str]:
        """Convert relative URL to absolute"""
        from urllib.parse import urljoin
        try:
            return urljoin(base_url, href)
        except:
            return None
    
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
                # Simple priority scoring
                priority = 0
                local_part = email.split('@')[0]
                
                # High priority: Looks like a name (contains dot or no generic keywords)
                if '.' in local_part and not any(k in local_part for k in GENERIC_EMAIL_PREFIXES):
                    priority = 2
                # Medium priority: Non-generic
                elif not any(k in local_part for k in GENERIC_EMAIL_PREFIXES):
                    priority = 1
                
                # Store email with priority (higher is better)
                # We'll handle selection later, for now just add all valid ones
                result['emails'].add((priority, email))
        
        # Extract phones
        phones = PHONE_PATTERN.findall(html)
        for phone in phones:
            # Fix 3: The "Scam" Blocker
            if self.is_fake_number(phone):
                continue

            # Clean and validate
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) == 10:
                # Format as (XXX) XXX-XXXX
                formatted = f"({clean_phone[:3]}) {clean_phone[3:6]}-{clean_phone[6:]}"
                result['phones'].add(formatted)
        
        # Extract doctor names / contact names using configured pattern
        if self.contact_pattern:
            doctors = self.contact_pattern.findall(html)
            for doctor in doctors:
                result['doctors'].add(doctor.strip())
        
        # Extract owner/founder names
        self.extract_owner_names(html, result)
    
    def extract_owner_names(self, html: str, result: Dict):
        """Extract owner/founder names from HTML and generate email patterns"""
        if not html:
            return
        
        # Clean HTML for text extraction
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ')
        
        owner_names = set()
        
        # Pattern 1: "Owner: John Smith"
        matches = OWNER_TITLE_PATTERN.findall(text)
        for match in matches:
            name = match.strip()
            if self.is_valid_owner_name(name):
                owner_names.add(name)
        
        # Pattern 2: "John Smith, Owner"
        matches = OWNER_AFTER_NAME_PATTERN.findall(text)
        for match in matches:
            name = match.strip()
            if self.is_valid_owner_name(name):
                owner_names.add(name)
    
    def is_valid_owner_name(self, name: str) -> bool:
        """Validate that a captured name is actually a person's name"""
        if not name:
            return False
        
        parts = name.split()
        
        # Must have at least first and last name
        if len(parts) < 2:
            return False
        
        # Each part must be at least 2 characters
        if any(len(part) < 2 for part in parts):
            return False
        
        # No part should be an invalid word
        for part in parts:
            if part.lower() in INVALID_NAME_WORDS:
                return False
        
        return True
        
        # Store owner names
        for name in owner_names:
            result['doctors'].add(f"Owner: {name}")
            logging.info(f"Found owner: {name}")
        
        # Generate email patterns for owners
        if owner_names and result.get('domain'):
            for name in owner_names:
                generated_emails = self.generate_owner_emails(name, result['domain'])
                for email in generated_emails:
                    # Priority 3 = highest for owner emails
                    result['emails'].add((3, email))
    
    def generate_tier1_email(self, name: str, domain: str) -> Tuple[str, str]:
        """Step 2b: The 'Guess & Verify' Loop for Tier 1 Emails"""
        # Split name: "John Smith" -> "john", "smith"
        parts = name.lower().split()
        if not parts: return "", ""
        
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        
        # 3 most common business email formats
        candidates = [
            f"{first}@{domain}" # john@hvac.com
        ]
        if last:
            candidates.append(f"{first}.{last}@{domain}") # john.smith@hvac.com
            candidates.append(f"{first}{last[0]}@{domain}") # johns@hvac.com
        
        # Check if these emails exist online (The Search Verification)
        for email in candidates:
            if self.verify_email_via_search(email):
                return email, "Tier 1 (Verified Owner)"
                
        # If we can't verify, return the most likely one but mark it "Unverified"
        return candidates[0], "Tier 1 (Unverified Guess)"

    def verify_email_via_search(self, email: str) -> bool:
        """Step 2c: Verify email existence via search echo"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(f'"{email}"', max_results=1))
                return len(results) > 0
        except:
            return False

    def find_owner_and_generate_email(self, company_name: str, domain: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Step 2: The 'Owner Hunt' - Find Owner Name via LinkedIn and guess email
        Returns: (email, confidence_source, owner_name)
        """
        logging.info(f"🕵️ Hunting Owner for: {company_name}")
        
        # 1. Search for the Who: "Company Owner Name"
        query = f'site:linkedin.com/in/ "{company_name}" "Owner" OR "Founder" OR "CEO"'
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=1))
                
                if results:
                    title = results[0]['title']
                    # LinkedIn titles usually look like: "John Smith - Owner - HVAC Co"
                    name_part = title.split(" - ")[0]
                   
                    # Check if it looks like a name (2-3 words)
                    if 1 < len(name_part.split()) <= 3:
                        logging.info(f"   ✅ Found Likely Owner: {name_part}")
                        
                        # Generate email
                        email, source = self.generate_tier1_email(name_part, domain)
                        return email, source, name_part
                        
        except Exception as e:
            logging.warning(f"   ⚠️ Search Error during Owner Hunt: {e}")
            
        return None, None, None

    def find_email_on_social(self, company_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Step 3: The 'Social Rescue' - Find Gmail/Outlook on Facebook
        """
        # Search for their Facebook 'About' page
        query = f'site:facebook.com "{company_name}" "Arizona" "@gmail.com" OR "@outlook.com"'
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=1))
                if results:
                    snippet = results[0]['body']
                    # Simple Regex to grab the email from the snippet
                    match = re.search(r'[\w\.-]+@[\w\.-]+', snippet)
                    if match:
                        return match.group(0), "Tier 2 (Social)"
        except:
            pass
        return None, None
    
    def hunter_domain_search(self, domain: str) -> Dict:
        """
        Use Hunter.io API to find emails and decision-makers for a domain.
        Free tier: 25 searches/month
        Returns: {'emails': [(priority, email)], 'people': [{'name': ..., 'position': ..., 'email': ...}]}
        """
        result = {'emails': [], 'people': []}
        
        # Load API key from environment
        api_key = os.environ.get('HUNTER_API_KEY', '')
        if not api_key:
            # Try loading from .env file
            env_path = os.path.join(BASE_DIR, '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('HUNTER_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            break
        
        if not api_key:
            logging.debug("Hunter.io API key not configured, skipping")
            return result
        
        try:
            # Hunter.io Domain Search API
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                emails_data = data.get('data', {}).get('emails', [])
                
                for email_info in emails_data:
                    email = email_info.get('value', '')
                    first_name = email_info.get('first_name', '')
                    last_name = email_info.get('last_name', '')
                    position = email_info.get('position', '').lower()
                    
                    if not email:
                        continue
                    
                    # Prioritize decision-makers
                    priority = 1
                    if any(title in position for title in ['owner', 'founder', 'ceo', 'president', 'principal']):
                        priority = 4  # Highest for owners
                        result['people'].append({
                            'name': f"{first_name} {last_name}".strip(),
                            'position': position,
                            'email': email
                        })
                    elif any(title in position for title in ['director', 'manager', 'vp', 'head']):
                        priority = 3  # High for management
                    elif first_name and last_name:
                        priority = 2  # Personal email
                    
                    result['emails'].append((priority, email))
                    
                logging.info(f"Hunter.io found {len(result['emails'])} emails for {domain}")
            elif response.status_code == 401:
                logging.warning("Hunter.io API key invalid")
            elif response.status_code == 429:
                logging.warning("Hunter.io rate limit reached")
            else:
                logging.warning(f"Hunter.io returned status {response.status_code}")
                
        except Exception as e:
            logging.error(f"Hunter.io search failed: {e}")
        
        return result
    
    def advanced_owner_search(self, domain: str) -> Dict:
        """
        Strategy 3: The 'Who' Search (LinkedIn/Facebook) + Permutation Generator
        Query: site:linkedin.com OR site:facebook.com "{domain}" "Owner" OR "CEO" OR "Founder"
        Returns: {'emails': [], 'owner_name': str}
        """
        result = {'emails': [], 'owner_name': ''}
        
        try:
            query = f'(site:linkedin.com/in/ OR site:facebook.com) "{domain}" (Owner OR CEO OR Founder OR Principal)'
            logging.info(f"Running Advanced 'Who' Search: {query}")
            
            with DDGS() as ddgs:
                # Get first 3 results
                results = list(ddgs.text(query, max_results=3))
                
                for r in results:
                    title = r.get('title', '')
                    body = r.get('body', '')
                    text = f"{title} {body}"
                    
                    # Extract Name using existing regex patterns
                    # We need to adapt the regex slightly or just look for names near titles
                    # Using a simple heuristic: Look for 2-word capitalized strings before/after title
                    name_match = OWNER_AFTER_NAME_PATTERN.search(title)
                    if not name_match:
                        name_match = OWNER_TITLE_PATTERN.search(title) # Try title format
                    
                    # Fallback: Split title by separator
                    if not name_match:
                        parts = title.split(' - ')
                        if len(parts) > 0 and self.is_valid_owner_name(parts[0]):
                             # Assume first part of LinkedIn title is name
                             name_match = re.match(r'([A-Z][a-z]+ [A-Z][a-z]+)', parts[0])

                    if name_match:
                        name = name_match.group(1).strip()
                        if self.is_valid_owner_name(name):
                            logging.info(f"Found Owner via Search: {name}")
                            result['owner_name'] = name
                            
                            # Step 2: Permutation Generator
                            permutations = self.generate_owner_emails(name, domain)
                            for email in permutations:
                                # Priority 3.5 (Higher than Hunter generic, lower than Hunter Proven)
                                result['emails'].append((3.5, email))
                            
                            break # Found best match
                            
        except Exception as e:
            logging.error(f"Advanced owner search failed: {e}")
            
        return result
    

    
    def verify_email_advanced(self, email: str, domain: str) -> Dict:
        """
        Verify email using Signals 1-3 instead of direct SMTP.
        Returns: {'score': int, 'signals': list, 'is_valid': bool}
        """
        result = {'score': 0, 'signals': [], 'is_valid': False}
        
        # Signal 1: MX Intelligence
        mx_score = self.analyze_mx_records(domain)
        result['score'] += mx_score
        if mx_score != 0:
            result['signals'].append(f"MX Score: {mx_score}")
            
        # Signal 2: Gravatar Hash Check
        if self.check_gravatar(email):
            result['score'] += 15
            result['signals'].append("Gravatar Found")
            
        # Signal 3: Search Echo Check
        if self.search_email_echo(email):
            result['score'] += 20
            result['signals'].append("Search Echo Found")
            
        # Decision Logic
        # Baseline score depends on source (set outside)
        # Here we just return the verification boost
        
        return result

    def analyze_mx_records(self, domain: str) -> int:
        """Signal 1: Check MX records for provider reputation"""
        score = 0
        try:
            records = dns.resolver.resolve(domain, 'MX')
            for r in records:
                exchange = str(r.exchange).lower()
                for provider, points in MX_PROVIDERS.items():
                    if provider in exchange:
                        score = points
                        logging.debug(f"MX Match: {provider} ({points}) for {domain}")
                        return score # Return on first match
        except Exception:
            pass
        return 0

    def check_gravatar(self, email: str) -> bool:
        """Signal 2: Check if email has a Gravatar"""
        try:
            hash_email = hashlib.md5(email.lower().strip().encode('utf-8')).hexdigest()
            url = f"https://www.gravatar.com/avatar/{hash_email}?d=404"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def search_email_echo(self, email: str) -> bool:
        """Signal 3: Check if email string appears in search results"""
        try:
            with DDGS() as ddgs:
                # Strict search for exact email
                results = list(ddgs.text(f'"{email}"', max_results=1))
                return len(results) > 0
        except:
            return False

    def is_fake_number(self, phone_string: str) -> bool:
        """Fix 3: The "Scam" Blocker (Stops the placeholders)"""
        bad_patterns = ["555", "123", "000", "666"]
        if any(p in phone_string for p in bad_patterns):
            return True
        return False

    def validate_business_site(self, url: str) -> bool:
        """
        Fix 1: The 'Anti-Directory' Filter
        Reject directory sites aggressively before scraping.
        """
        # 1. The "Waste of Time" List (Merged with existing global list)
        blocklist = BLACKLIST_DOMAINS # Already updated above with user's list
        
        # 2. Check URL
        domain = url.lower()
        if any(x in domain for x in blocklist):
            return False
            
        if any(bad in domain for bad in NON_BUSINESS_KEYWORDS):
             return False
             
        return True

    def clean_email_string(self, email: str) -> str:
        """Fix 2b: The String Cleaner - Remove artifacts"""
        import urllib.parse
        # Decodes URL characters (removes %20)
        email = urllib.parse.unquote(email)
        # Removes leading/trailing whitespace and hidden characters
        email = email.strip().replace(" ", "")
        # Removes common scraping artifacts like leading hyphens
        email = email.lstrip("-.")
        return email

    def is_valid_lead(self, email: str, domain: str) -> bool:
        """Fix 2: Strict Email Sanity Filter"""
        if not email: return False
        email = email.lower()
        
        # 1. Block common trash patterns
        if any(x in email for x in EMAIL_JUNK_STRINGS):
            return False
            
        # 2. Block Directory Sites
        email_domain = email.split('@')[-1]
        if any(bad in email_domain for bad in BLACKLIST_DOMAINS):
            return False
            
        # 3. Domain Mismatch Check (Fix 1: The "Domain Lock")
        # Only accept an email if it matches the website's domain.
        if domain:
            email_domain = email.split('@')[-1]
            
            # STRICT CHECK: They must match or overlap
            if domain in email_domain or email_domain in domain:
                pass # Matched
            else:
                # Allow generic providers if it's a small business using gmail/outlook
                is_provider = False
                for provider in ['gmail', 'outlook', 'yahoo', 'hotmail', 'icloud', 'aol']:
                    if provider in email_domain:
                        is_provider = True
                        break
                
                if not is_provider:
                    logging.debug(f"⚠️ REJECTED: {email} does not match domain {domain}")
                    return False
        
        # 4. Length check
        local_part = email.split('@')[0]
        if len(local_part) < 3:
            return False
            
        return True

    def categorize_email_role(self, email: str) -> Tuple[str, str]:
        """
        Determine Email Tier and Role based on user rules.
        Tier 1: Owner / Decision Maker (Named)
        Tier 2: Strong Generic (info, office, hello)
        Tier 3: Operational (support, service, billing)
        """
        local_part = email.split('@')[0].lower()
        
        # Tier 3: Operational
        operational_keywords = ['support', 'service', 'billing', 'sales', 'help', 'returns', 'orders']
        if any(k in local_part for k in operational_keywords):
            return "Tier 3 (Operational)", "operational"
            
        # Tier 2: Strong Generic
        generic_keywords = ['info', 'office', 'hello', 'contact', 'admin', 'inquiry']
        if any(k in local_part for k in generic_keywords):
            return "Tier 2 (Strong Generic)", "generic"
            
        # Tier 1: Owner / Named
        # If it's not generic/operational, and has valid format, assume named/owner potential
        return "Tier 1 (Decision Maker)", "owner"

    def prioritize_contacts(self, emails: set, phones: set, domain: str = "") -> Tuple[str, str, str]:
        """Fix 4: The Priority Sorter - Implement Correct Tier 1/2/3 Logic & Role"""
        email_list = list(emails)
        valid_emails = []
        
        for e in email_list:
            email_str = e[1] if isinstance(e, tuple) else e
            cleaned = self.clean_email_string(email_str)
            if self.is_valid_lead(cleaned, domain):
                # Calculate Tier/Role immediately
                tier, role = self.categorize_email_role(cleaned)
                # Assign numeric score for sorting (Lower is better)
                score = 1 if role == 'owner' else 2 if role == 'generic' else 3
                valid_emails.append((score, cleaned, tier, role))
        
        # Sort by Score (Ascending)
        valid_emails.sort(key=lambda x: x[0])
        
        best_email = ""
        best_tier = ""
        best_role = ""
        
        if valid_emails:
            best_email = valid_emails[0][1]
            best_tier = valid_emails[0][2]
            best_role = valid_emails[0][3]
            
        # Phone logic
        best_phone = list(phones)[0] if phones else ""
        
        return best_email, best_phone, best_role

    
    def enrich_lead(self, row: Dict) -> Dict:
        """
        Main enrichment function for a single lead
        """
        business_name = row.get(self.cols['name'], '')
        # Fallback for location if missing or empty
        location = row.get(self.cols['location'], '')
        if not location and 'AZ' in str(row): # Simple heuristic if location missing
             location = "Arizona, United States"
        
        logging.info(f"Processing: {business_name} - {location}")
        
        enriched = {
            # Website intentionally omitted here to prevent overwriting with empty string
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
        
        # If search failed, try using existing website from row
        if not website:
             # Try 'Website' or 'website'
             existing_website = row.get('Website', row.get('website', ''))
             if existing_website and not any(site in existing_website.lower() for site in BLACKLIST_DOMAINS):
                 website = existing_website
                 logging.info(f"Using existing website: {website}")

        if website:
            # Fix 1: Business Ownership Gate
            if not self.validate_business_site(website):
                logging.info(f"Skipping non-business website: {website}")
                enriched['Scrape Status'] = 'Skipped (Non-Business)'
            else:
                enriched['Website'] = website
                self.rate_limit_delay()
                
                scrape_result = self.scrape_website(website)
            
            if scrape_result['emails'] or scrape_result['phones']:
                # Handle Emails and Phones with Priority logic (Fix 4)
                best_email, best_phone, email_role = self.prioritize_contacts(
                    scrape_result['emails'], 
                    scrape_result['phones'],
                    scrape_result.get('domain', '')
                )
                
                if best_email:
                    enriched['Email_Primary'] = best_email
                    enriched['Email_Confidence'] = scrape_result['confidence']
                    enriched['Email_Source'] = self.categorize_email_role(best_email)[0] # Get Tier string
                    enriched['email_role'] = email_role
                
                if best_phone:
                    enriched['Phone_Primary'] = best_phone
                    enriched['Phone_Validated'] = 'True'
                    enriched['Phone_Source'] = 'Website Direct'
                
                if scrape_result['doctors']:
                    enriched['Doctor_Name'] = ', '.join(list(scrape_result['doctors'])[:3])
            
            # Strategy 2 & 3: Owner Discovery & Inference (The "Separate Agent" logic - Fix 3)
            # We always try to find the owner, even if we scraped a generic email like info@
            
            # Check if we already have a high-quality personal email (Tier 1)
            has_personal_email = False
            if 'Tier 1' in enriched.get('Email_Source', ''):
                has_personal_email = True
                
            # If we don't have a personal email, or if we want to enrich owner data anyway:
            if not has_personal_email: 
                # Step 2: The Owner Hunt (User Request)
                # Should we use domain? What if no domain?
                # The user's snippet uses domain for generating email.
                # If we have a domain (from website search), use it. 
                # If not, we might fail step 2, which is fine, fallback to Social.
                
                hunt_domain = scrape_result.get('domain')
                if not hunt_domain and website:
                    # Parse from website if scrape_result missing it
                     try: 
                        from urllib.parse import urlparse
                        hunt_domain = urlparse(website).netloc.replace('www.', '')
                     except: pass
                
                if hunt_domain:
                    owner_email, owner_source, owner_name = self.find_owner_and_generate_email(business_name, hunt_domain)
                    
                    if owner_email:
                         # Found one!
                         enriched['Email_Primary'] = owner_email
                         enriched['Email_Source'] = owner_source
                         enriched['Email_Confidence'] = 85 if 'Verified' in owner_source else 50
                         if owner_name:
                             enriched['Doctor_Name'] = f"{owner_name} (Owner)"
                         has_personal_email = True

            # Step 3: Social Rescue (User Request)
            # Use this if we still have no email at all
            if not enriched['Email_Primary']:
                social_email, social_source = self.find_email_on_social(business_name)
                if social_email:
                    # Sanity check the social email
                    if self.is_valid_lead(social_email, ""):
                         enriched['Email_Primary'] = social_email
                         enriched['Email_Source'] = social_source
                         enriched['Email_Confidence'] = 60 # Social is Tier 2
                         logging.info(f"✅ Social Rescue found email: {social_email}")
                
            # Old fallback logic (Hunter/Advanced) logic removed as it's superseded by Owner Hunt
            # (Or we can keep it as extra backup, but user replaced it explicitly)
            # I will remove the old complicated blocks to keep it clean as requested.


        
        return enriched
    
    def calculate_priority(self, row: Dict) -> int:
        """Calculate processing priority for a lead"""
        try:
            rating_str = row.get(self.cols['rating'], '0')
            if not rating_str: rating_str = '0'
            rating = float(rating_str.replace(',', '.'))
            
            reviews_str = row.get(self.cols['reviews'], '0')
            if not reviews_str: reviews_str = '0'
            review_count = int(re.sub(r'[^\d]', '', reviews_str)) if reviews_str else 0
            
            services = row.get(self.cols['services'], '').lower()
            if not services: services = ''
            
            # Get thresholds from config
            min_revs = self.config.get('filter_min_reviews', 100)
            max_revs = self.config.get('filter_max_reviews', 1000)
            priority_keywords = self.config.get('priority_keywords', ['on-site', 'emergency'])
            
            # Priority 1: High value in range
            if rating >= 4.8 and review_count >= min_revs:
                return 1
            # Priority 2: Good value in range
            elif rating >= 4.5 and review_count >= (min_revs / 2):
                return 2
            # Priority 3: Keywords
            elif any(k in services for k in priority_keywords):
                return 3
            else:
                return 4
        except:
            return 5
    
    def process_leads(self):
        """Main processing function"""
        if not os.path.exists(self.input_file):
            logging.error(f"Input file not found: {self.input_file}")
            return
        
        # Read input
        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                # Sanitize fieldnames (strip whitespace)
                if reader.fieldnames:
                    reader.fieldnames = [name.strip() for name in reader.fieldnames]
                fieldnames = reader.fieldnames
                rows = list(reader)
                
                # Debug logging for columns
                if rows:
                    logging.info(f"CSV Columns: {list(rows[0].keys())}")
                    logging.info(f"First row name check: {rows[0].get(self.cols['name'], 'NOT FOUND')}")
        except Exception as e:
            logging.error(f"Error reading CSV: {e}")
            return
        
        logging.info(f"Loaded {len(rows)} leads")
        
        # Sort by priority
        rows_with_priority = [(self.calculate_priority(row), row) for row in rows]
        rows_with_priority.sort(key=lambda x: x[0])
        sorted_rows = [row for _, row in rows_with_priority]
        
        # Prepare output fieldnames (deduplicate 'Website')
        new_columns = [
            'Website', 'Email_Primary', 'Email_Confidence', 'Email_Source',
            'Phone_Primary', 'Phone_Validated', 'Phone_Source',
            'Doctor_Name', 'Last_Updated'
        ]
        # Only add columns that are not already in fieldnames
        output_fieldnames = list(fieldnames) + [c for c in new_columns if c not in fieldnames]
        
        enriched_rows = []
        start_from = self.progress.get('last_processed', 0)
        
        # FIX: Load existing rows if resuming to prevent data loss
        if start_from > 0 and os.path.exists(self.output_file):
            try:
                logging.info(f"Resuming: Loading existing leads from {self.output_file}")
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    enriched_rows = list(reader)
            except Exception as e:
                logging.error(f"Failed to load existing output: {e}")
                # Fallback: Don't lose new data, but old data might be lost in file if overwritten
                # We'll rely on the user having a backup or just proceed

        
        try:
            for i, row in enumerate(sorted_rows[start_from:], start=start_from):
                business_name = row.get(self.cols['name'], '')
                
                # Skip if already processed
                if business_name and business_name in self.progress.get('processed_names', []):
                    logging.info(f"Skipping already processed: {business_name}")
                    continue
                
                logging.info(f"Progress: {i+1}/{len(rows)}")
                
                # Enrich the lead
                try:
                    enriched_data = self.enrich_lead(row)
                except Exception as e:
                    logging.error(f"Critical error enriching lead {business_name}: {e}")
                    enriched_data = {'Scrape Status': f'Error: {str(e)}'}
                
                # Merge with original data
                enriched_row = {**row, **enriched_data}
                enriched_rows.append(enriched_row)
                
                # Update progress
                self.progress['last_processed'] = i + 1
                if 'processed_names' not in self.progress:
                    self.progress['processed_names'] = []
                self.progress['processed_names'].append(business_name)
                
                # Save progress every 10 records
                if (i + 1) % 10 == 0:
                    self.save_progress()
                    self.save_output(enriched_rows, output_fieldnames)
                    logging.info(f"Progress saved: {i+1} leads processed")
                
                # Rate limiting
                self.rate_limit_delay()
                
        except KeyboardInterrupt:
            logging.info("Process interrupted. Saving progress...")
            self.save_progress()
            return
        
        # Final save
        self.save_output(enriched_rows, output_fieldnames)
        self.save_progress()
        
        logging.info(f"✓ Enrichment complete! Output saved to: {self.output_file}")
        logging.info(f"Processed {len(enriched_rows)} leads")
    
    def save_output(self, rows: list, fieldnames: list):
        """Save enriched data to CSV"""
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    import argparse
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description='Enrich leads using a specific profile.')
    parser.add_argument('--profile', type=str, default='hvac', help='Profile name from profiles.json (default: hvac)')
    args = parser.parse_args()
    
    logging.info("=" * 60)
    logging.info(f"Starting Google Leads Enrichment Process (Profile: {args.profile})")
    logging.info("=" * 60)
    
    # Load profiles.json
    profile_path = os.path.join(BASE_DIR, 'profiles.json')
    config = None
    
    if os.path.exists(profile_path):
        try:
            with open(profile_path, 'r') as f:
                profiles = json.load(f)
            
            # Use specified profile
            profile_name = args.profile
            if profile_name in profiles:
                config = profiles[profile_name]
                logging.info(f"Loaded configuration for profile: {profile_name}")
                
                # Resolving paths
                if config.get('input_file') and not os.path.isabs(config['input_file']):
                    config['input_file'] = os.path.join(BASE_DIR, config['input_file'])
                if config.get('output_file') and not os.path.isabs(config['output_file']):
                    config['output_file'] = os.path.join(BASE_DIR, config['output_file'])
            else:
                logging.warning(f"Profile '{profile_name}' not found in profiles.json")
        except Exception as e:
            logging.error(f"Error loading profiles.json: {e}")
    
    if not config:
        logging.warning("Falling back to default dentist configuration")
        config = {
            'keyword': 'dentist',
            'contact_title_pattern': r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        }
    
    enricher = LeadEnricher(config=config, input_file=config.get('input_file'), output_file=config.get('output_file'))
    enricher.process_leads()
