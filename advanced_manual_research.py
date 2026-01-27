import csv
import re
import requests
import time
import dns.resolver
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

class AdvancedEmailResearcher:
    """
    Advanced manual research for leads without emails
    Uses multiple techniques to find personal or generic emails
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    def get_whois_email(self, domain):
        """Extract email from WHOIS data"""
        try:
            import whois
            w = whois.whois(domain)
            if w.emails:
                return w.emails[0] if isinstance(w.emails, list) else w.emails
        except:
            pass
        return None
    
    def get_mx_records(self, domain):
        """Get email server info from DNS MX records"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return [str(r.exchange) for r in mx_records]
        except:
            return []
    
    def google_email_search(self, company_name, domain):
        """Search Google for company email mentions"""
        try:
            # Search for email mentions
            query = f'"{company_name}" email contact site:{domain}'
            search_url = f'https://www.google.com/search?q={query}'
            
            response = self.session.get(search_url, timeout=10)
            
            # Extract emails from results
            email_pattern = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
            emails = re.findall(email_pattern, response.text, re.IGNORECASE)
            
            return set(emails)
        except:
            return set()
    
    def extract_owner_name_from_about(self, url):
        """Scrape 'About' page for owner/founder name"""
        try:
            about_urls = [
                f"{url}/about",
                f"{url}/about-us",
                f"{url}/our-team",
                f"{url}/team",
                f"{url}/company"
            ]
            
            for about_url in about_urls:
                try:
                    response = self.session.get(about_url, timeout=10)
                    text = response.text.lower()
                    
                    # Look for owner/founder patterns
                    patterns = [
                        r'(?:owner|founder|president|ceo)[\s:]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        r'([A-Z][a-z]+\s+[A-Z][a-z]+)[\s,]+(?:owner|founder|president|ceo)'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, response.text)
                        if matches:
                            return matches[0]
                except:
                    continue
                    
        except:
            pass
        return None
    
    def generate_email_patterns(self, name, domain):
        """Generate possible email patterns from name"""
        if not name:
            return []
        
        parts = name.lower().split()
        if len(parts) < 2:
            return []
        
        first, last = parts[0], parts[-1]
        
        patterns = [
            f"{first}@{domain}",
            f"{first}.{last}@{domain}",
            f"{first}{last}@{domain}",
            f"{last}@{domain}",
            f"{first[0]}{last}@{domain}",
        ]
        
        return patterns
    
    def find_email_for_lead(self, business_name, website):
        """Main research function - tries all techniques"""
        logging.info(f"\nResearching: {business_name[:50]}")
        logging.info(f"Website: {website}")
        
        domain = urlparse(website).netloc.replace('www.', '')
        results = {
            'emails_found': [],
            'techniques_used': [],
            'owner_name': None
        }
        
        # 1. WHOIS lookup
        whois_email = self.get_whois_email(domain)
        if whois_email and domain in whois_email:
            results['emails_found'].append(('whois', whois_email))
            results['techniques_used'].append('WHOIS')
            logging.info(f"  [WHOIS] {whois_email}")
        
        # 2. Google search
        google_emails = self.google_email_search(business_name, domain)
        for email in google_emails:
            results['emails_found'].append(('google', email))
            results['techniques_used'].append('Google')
            logging.info(f"  [Google] {email}")
        
        # 3. Extract owner name
        owner_name = self.extract_owner_name_from_about(website)
        if owner_name:
            results['owner_name'] = owner_name
            logging.info(f"  [Owner Found] {owner_name}")
            
            # 4. Generate and test patterns
            patterns = self.generate_email_patterns(owner_name, domain)
            for pattern in patterns:
                results['emails_found'].append(('pattern', pattern))
                logging.info(f"  [Pattern] {pattern}")
        
        # 5. Common patterns
        common = [f"info@{domain}", f"contact@{domain}", f"hello@{domain}"]
        for email in common:
            results['emails_found'].append(('common', email))
        
        time.sleep(2)  # Rate limiting
        return results

# Main execution
input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

researcher = AdvancedEmailResearcher()

# Load leads
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

logging.info("="*60)
logging.info("Advanced Manual Research for 21 Leads Without Emails")
logging.info("="*60)

found_count = 0
processed = 0

for row in rows:
    if row.get('email') or not row.get('website'):
        continue
    
    processed += 1
    name = row.get('business_name', '')
    website = row.get('website', '')
    
    # Research this lead
    results = researcher.find_email_for_lead(name, website)
    
    if results['emails_found']:
        # Pick best email
        best = results['emails_found'][0][1]
        row['email'] = best
        row['email_role'] = 'generic'  # Default
        row['email_tier'] = '2'
        row['Email_Source'] = f"Manual Research: {results['techniques_used'][0]}"
        found_count += 1
        logging.info(f"  => Selected: {best}")

# Save
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

logging.info(f"\n{'='*60}")
logging.info(f"Manual Research Complete")
logging.info(f"Processed: {processed} leads")
logging.info(f"Found: {found_count} new emails")
logging.info(f"Success Rate: {(found_count/processed*100):.1f}%" if processed > 0 else "N/A")
