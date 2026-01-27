import csv
import os
import sys
import logging

# Deep enrichment for Ohio leads
sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher

logging.basicConfig(level=logging.INFO, format='%(message)s')

input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

enricher = LeadEnricher(config={"keyword": "hvac"})

# Load current leads
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

logging.info(f"🔍 Starting Deep Enrichment for Ohio Leads")
logging.info(f"Total Leads: {len(rows)}")
logging.info(f"=" * 60)

upgraded = 0
processed = 0

for i, row in enumerate(rows, 1):
    name = row.get('business_name', '')
    website = row.get('website', '')
    existing_email = row.get('email', '')
    
    # Only process leads without emails
    if existing_email:
        continue
        
    processed += 1
    logging.info(f"[{i}/{len(rows)}] Processing: {name[:50]}")
    
    # Extract domain from website
    domain = ''
    if website:
        try:
            from urllib.parse import urlparse
            domain = urlparse(website).netloc.replace('www.', '')
        except:
            pass
    
    # Step 1: Owner Hunt (LinkedIn search)
    if domain:
        owner_email, owner_source, owner_name = enricher.find_owner_and_generate_email(name, domain)
        
        if owner_email:
            row['email'] = owner_email
            row['Email_Source'] = owner_source
            row['email_role'] = 'owner'
            row['email_tier'] = '1'
            logging.info(f"   ✅ Owner Hunt: {owner_email} ({owner_source})")
            upgraded += 1
            continue
    
    # Step 2: Social Rescue (Facebook fallback)
    social_email, social_source = enricher.find_email_on_social(name)
    
    if social_email and enricher.is_valid_lead(social_email, domain or ""):
        tier_string, role = enricher.categorize_email_role(social_email)
        row['email'] = social_email
        row['Email_Source'] = social_source
        row['email_role'] = role
        row['email_tier'] = '2'  # Social is Tier 2
        logging.info(f"   ✅ Social Rescue: {social_email}")
        upgraded += 1

# Save results
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

logging.info(f"\n" + "=" * 60)
logging.info(f"✅ Deep Enrichment Complete!")
logging.info(f"Processed: {processed} leads without emails")
logging.info(f"Upgraded: {upgraded} leads found new emails")
logging.info(f"Success Rate: {(upgraded/processed*100):.1f}%" if processed > 0 else "N/A")
logging.info(f"\n📁 Saved to: {output_file}")
