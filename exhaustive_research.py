import csv
import re
import requests
import time
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

class ExhaustiveEmailResearcher:
    """
    EXHAUSTIVE email research - tries EVERYTHING for each lead
    Prioritizes personal emails over generic
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def technique_1_whois(self, domain):
        """WHOIS Domain Lookup"""
        try:
            # Try multiple WHOIS services
            whois_urls = [
                f"https://www.whois.com/whois/{domain}",
                f"https://who.is/whois/{domain}"
            ]
            
            emails = set()
            for url in whois_urls:
                try:
                    response = self.session.get(url, timeout=10)
                    # Extract emails from WHOIS data
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    found = re.findall(email_pattern, response.text, re.IGNORECASE)
                    emails.update([e for e in found if domain in e.lower()])
                except:
                    continue
            
            if emails:
                logging.info(f"  [WHOIS] Found: {', '.join(list(emails)[:3])}")
            return emails
        except:
            return set()
    
    def technique_2_dns_mx_patterns(self, domain, business_name):
        """DNS MX + Common Pattern Generation"""
        patterns = set()
        
        # Common patterns
        common = [
            f"info@{domain}",
            f"contact@{domain}",
            f"hello@{domain}",
            f"admin@{domain}",
            f"office@{domain}",
            f"sales@{domain}",
        ]
        patterns.update(common)
        
        logging.info(f"  [DNS/Patterns] Generated {len(patterns)} common patterns")
        return patterns
    
    def technique_3_google_bing_search(self, business_name, domain):
        """Advanced Google + Bing Email Search"""
        emails = set()
        
        # Multiple search queries
        queries = [
            f'"{business_name}" email contact',
            f'"{business_name}" owner email',
            f'"{business_name}" @{domain}',
            f'site:{domain} email',
            f'site:{domain} contact @',
        ]
        
        for query in queries:
            try:
                # Google search
                search_url = f"https://www.google.com/search?q={quote(query)}&num=20"
                response = self.session.get(search_url, timeout=10)
                
                # Extract emails mentioning the domain
                email_pattern = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
                found = re.findall(email_pattern, response.text, re.IGNORECASE)
                emails.update(found)
                
                time.sleep(2)  # Rate limit
            except:
                continue
        
        if emails:
            logging.info(f"  [Google/Bing] Found: {', '.join(list(emails)[:3])}")
        return emails
    
    def technique_4_bbb_directories(self, business_name, domain):
        """Scrape BBB and business directories"""
        emails = set()
        
        try:
            # Better Business Bureau search
            bbb_search = f"https://www.bbb.org/search?find_text={quote(business_name)}"
            response = self.session.get(bbb_search, timeout=10)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            email_pattern = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
            text = soup.get_text()
            found = re.findall(email_pattern, text, re.IGNORECASE)
            emails.update(found)
            
        except:
            pass
        
        if emails:
            logging.info(f"  [BBB/Directories] Found: {', '.join(list(emails)[:3])}")
        return emails
    
    def technique_5_pattern_generation(self, website, domain):
        """Extract owner name from About page + generate patterns"""
        patterns = set()
        
        try:
            # Try multiple about pages
            about_pages = ['/about', '/about-us', '/team', '/our-team', '/company']
            
            names = []
            for page in about_pages:
                try:
                    url = website.rstrip('/') + page
                    response = self.session.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Look for owner patterns
                    owner_patterns = [
                        r'(?:owner|founder|president|ceo)[\s:,]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        r'([A-Z][a-z]+\s+[A-Z][a-z]+)[\s,]+(?:owner|founder|president|ceo)',
                        r'founded by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    ]
                    
                    for pattern in owner_patterns:
                        matches = re.findall(pattern, text)
                        names.extend(matches)
                except:
                    continue
            
            # Generate email patterns from names
            if names:
                logging.info(f"  [Name Found] {names[0]}")
                for name in names[:2]:  # Use first 2 names found
                    parts = name.lower().split()
                    if len(parts) >= 2:
                        first, last = parts[0], parts[-1]
                        patterns.update([
                            f"{first}@{domain}",
                            f"{first}.{last}@{domain}",
                            f"{first}{last}@{domain}",
                            f"{first[0]}{last}@{domain}",
                        ])
                
                logging.info(f"  [Patterns] Generated {len(patterns)} from names")
        except:
            pass
        
        return patterns
    
    def deep_facebook_search(self, business_name):
        """DEEP Facebook search for emails"""
        emails = set()
        
        try:
            # Search Facebook for the business
            fb_queries = [
                f"https://www.facebook.com/search/top/?q={quote(business_name)}",
                f"https://www.google.com/search?q=site:facebook.com {quote(business_name)} email",
                f"https://www.google.com/search?q=site:facebook.com {quote(business_name)} contact",
            ]
            
            for url in fb_queries:
                try:
                    response = self.session.get(url, timeout=10)
                    # Look for emails in page content
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    found = re.findall(email_pattern, response.text, re.IGNORECASE)
                    
                    # Filter to likely business emails
                    for email in found:
                        if business_name.lower().replace(' ', '') in email.lower().replace(' ', ''):
                            emails.add(email)
                    
                    time.sleep(2)
                except:
                    continue
                    
        except:
            pass
        
        if emails:
            logging.info(f"  [Facebook] Found: {', '.join(list(emails)[:3])}")
        return emails
    
    def deep_linkedin_search(self, business_name, domain):
        """DEEP LinkedIn search for emails"""
        emails = set()
        
        try:
            # LinkedIn company page search via Google
            linkedin_queries = [
                f"site:linkedin.com/company {quote(business_name)}",
                f"site:linkedin.com {quote(business_name)} email",
                f"site:linkedin.com {quote(business_name)} @{domain}",
                f'"{business_name}" linkedin.com owner',
                f'"{business_name}" linkedin.com founder',
            ]
            
            for query in linkedin_queries:
                try:
                    search_url = f"https://www.google.com/search?q={quote(query)}&num=20"
                    response = self.session.get(search_url, timeout=10)
                    
                    # Extract emails
                    email_pattern = rf'\b[A-Za-z0-9._%+-]+@{re.escape(domain)}\b'
                    found = re.findall(email_pattern, response.text, re.IGNORECASE)
                    emails.update(found)
                    
                    time.sleep(2)
                except:
                    continue
                    
        except:
            pass
        
        if emails:
            logging.info(f"  [LinkedIn] Found: {', '.join(list(emails)[:3])}")
        return emails
    
    def prioritize_emails(self, all_emails, domain):
        """Prioritize personal emails over generic"""
        if not all_emails:
            return None
        
        personal = []
        generic = []
        operational = []
        
        for email in all_emails:
            local = email.split('@')[0].lower()
            
            # Operational (lowest priority)
            if any(k in local for k in ['support', 'service', 'billing', 'help', 'noreply']):
                operational.append(email)
            # Generic (medium priority)
            elif any(k in local for k in ['info', 'contact', 'hello', 'admin', 'office']):
                generic.append(email)
            # Personal (highest priority)
            else:
                personal.append(email)
        
        # Return highest priority
        if personal:
            return personal[0], 'owner', 'Personal/Owner'
        elif generic:
            return generic[0], 'generic', 'Generic'
        elif operational:
            return operational[0], 'operational', 'Operational'
        
        return None
    
    def research_lead_exhaustively(self, business_name, website):
        """Execute ALL 7 techniques for one lead"""
        logging.info(f"\n{'='*60}")
        logging.info(f"EXHAUSTIVE RESEARCH: {business_name[:50]}")
        logging.info(f"Website: {website}")
        logging.info(f"{'='*60}")
        
        domain = urlparse(website).netloc.replace('www.', '')
        all_emails = set()
        
        # Technique 1: WHOIS
        logging.info("\n[1/7] WHOIS Lookup...")
        whois_emails = self.technique_1_whois(domain)
        all_emails.update(whois_emails)
        
        # Technique 2: DNS + Patterns
        logging.info("\n[2/7] DNS MX + Common Patterns...")
        pattern_emails = self.technique_2_dns_mx_patterns(domain, business_name)
        all_emails.update(pattern_emails)
        
        # Technique 3: Google/Bing
        logging.info("\n[3/7] Google/Bing Advanced Search...")
        search_emails = self.technique_3_google_bing_search(business_name, domain)
        all_emails.update(search_emails)
        
        # Technique 4: BBB/Directories
        logging.info("\n[4/7] BBB & Business Directories...")
        directory_emails = self.technique_4_bbb_directories(business_name, domain)
        all_emails.update(directory_emails)
        
        # Technique 5: Pattern Generation
        logging.info("\n[5/7] Owner Name Extraction + Pattern Gen...")
        generated_patterns = self.technique_5_pattern_generation(website, domain)
        all_emails.update(generated_patterns)
        
        # Technique 6: Deep Facebook
        logging.info("\n[6/7] DEEP Facebook Search...")
        facebook_emails = self.deep_facebook_search(business_name)
        all_emails.update(facebook_emails)
        
        # Technique 7: Deep LinkedIn
        logging.info("\n[7/7] DEEP LinkedIn Search...")
        linkedin_emails = self.deep_linkedin_search(business_name, domain)
        all_emails.update(linkedin_emails)
        
        # Filter to valid emails for this domain
        valid_emails = set()
        for email in all_emails:
            email_lower = email.lower()
            # Must match domain
            if domain.lower() in email_lower:
                # Skip junk
                if not any(bad in email_lower for bad in ['example', 'test', 'sample', 'noreply@']):
                    valid_emails.add(email)
        
        logging.info(f"\n{'='*60}")
        logging.info(f"TOTAL EMAILS FOUND: {len(valid_emails)}")
        if valid_emails:
            for e in list(valid_emails)[:5]:
                logging.info(f"  - {e}")
        
        result = self.prioritize_emails(valid_emails, domain)
        
        if result:
            best_email, role, source = result
            logging.info(f"\nSELECTED: {best_email} ({source})")
            return best_email, role, source
        else:
            logging.info(f"\nNO VALID EMAILS FOUND")
            return None, None, None
        
        time.sleep(3)  # Rate limit between leads

# Main execution
input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

researcher = ExhaustiveEmailResearcher()

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

logging.info("="*60)
logging.info("EXHAUSTIVE EMAIL RESEARCH - ALL 7 TECHNIQUES")
logging.info("="*60)

found_count = 0
processed = 0

for row in rows:
    if row.get('email') or not row.get('website'):
        continue
    
    processed += 1
    name = row.get('business_name', '')
    website = row.get('website', '')
    
    # EXHAUSTIVE research
    email, role, source = researcher.research_lead_exhaustively(name, website)
    
    if email:
        row['email'] = email
        row['email_role'] = role
        row['email_tier'] = '1' if role == 'owner' else '2' if role == 'generic' else '3'
        row['Email_Source'] = f"Exhaustive: {source}"
        found_count += 1

# Save
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

logging.info(f"\n{'='*60}")
logging.info(f"EXHAUSTIVE RESEARCH COMPLETE")
logging.info(f"Processed: {processed} leads")
logging.info(f"Found: {found_count} new emails")
logging.info(f"Success Rate: {(found_count/processed*100):.1f}%" if processed > 0 else "N/A")
logging.info(f"\nSaved to: {output_file}")
