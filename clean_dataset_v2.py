
import csv
import os
import sys
from urllib.parse import urlparse
sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher, BLACKLIST_DOMAINS

def clean_dataset_v2():
    input_file = r"c:\Users\Piyush\Downloads\lead enreaching agent\smart_leads_HVAC_Arizona_enriched.csv"
    output_file = input_file
    
    if not os.path.exists(input_file):
        print("File not found.")
        return

    enricher = LeadEnricher()
    
    # Add specific problem domains to blacklist for this cleanup
    BAD_DOMAINS = BLACKLIST_DOMAINS + ['delhi.gov.in', 'reddit.com', 'wiktionary.org']
    
    cleaned_rows = []
    fieldnames = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        print(f"Columns found: {fieldnames}")
        
        for i, row in enumerate(reader):
            website = row.get('Website', '')
            email = row.get('Email_Primary', '')
            phone = row.get('Phone_Primary', '')
            business_name = row.get('business_name', 'Unknown')
            
            # 0. Validate Website URL first (Root Cause Fix)
            domain = ""
            if website:
                try:
                    domain = urlparse(website).netloc.replace('www.', '')
                    # Check against blacklist
                    if any(bad in domain for bad in BAD_DOMAINS):
                        print(f"🚫 [Website] Removed blacklisted website for {business_name}: {website}")
                        row['Website'] = ''
                        website = ''
                        domain = ''
                        # Also nuke email if it matched this bad domain
                        if email and domain in email:
                             row['Email_Primary'] = ''
                             email = ''
                except: pass

            # 1. Email Check (Domain Lock)
            if email:
                # If website is gone/empty, we can't strict verify match, 
                # but if we have a domain (from valid website), it MUST match
                if domain:
                    if not enricher.is_valid_lead(email, domain):
                        print(f"🚫 [Email] Domain Lock rejected for {business_name}: {email} vs {domain}")
                        row['Email_Primary'] = ''
                        row['Email_Confidence'] = ''
                        row['Email_Source'] = ''
                else:
                    # No website to verify against? 
                    # If email is generic public domain (gmail etc) it's ok?
                    # If it's something weird, maybe suspicious. 
                    # For now keep it unless it looks like junk.
                    if not enricher.is_valid_lead(email, ""):
                         print(f"🚫 [Email] Sanity check rejected for {business_name}: {email}")
                         row['Email_Primary'] = ''

            # 2. Phone Check (Scam Blocker)
            if phone:
                if enricher.is_fake_number(phone):
                    print(f"🚫 [Phone] Scam Blocker removed for {business_name}: {phone}")
                    row['Phone_Primary'] = ''
                    row['Phone_Validated'] = 'False'
                    row['Phone_Source'] = ''
            
            # Clean extra fields
            if None in row:
                del row[None]
                
            cleaned_rows.append(row)

    # Save
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    print(f"Done. Cleaned {len(cleaned_rows)} rows.")

if __name__ == "__main__":
    clean_dataset_v2()
