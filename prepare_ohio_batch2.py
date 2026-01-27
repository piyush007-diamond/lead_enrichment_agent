import csv
import sys
from urllib.parse import urlparse

# File paths
new_leads_file = "C:/Users/Piyush/Downloads/google (2).csv"
existing_leads_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "ohio_batch2_to_enrich.csv"

print("Starting processing...")

# 1. Load existing leads
existing_websites = set()
existing_names = set()

try:
    with open(existing_leads_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('website'):
                try:
                    domain = urlparse(row['website']).netloc.replace('www.', '').lower()
                    if domain: existing_websites.add(domain)
                except: pass
            if row.get('business_name'):
                existing_names.add(row['business_name'].lower().strip())
except Exception as e:
    print(f"Warning loading existing: {e}")

print(f"Loaded {len(existing_websites)} existing websites, {len(existing_names)} names.")

# 2. Process new leads
new_leads = []
seen_current_batch = set()
bad_patterns = ['trane.com', 'find-a-dealer', 'servicetitan', 'expertise.com', 'networx.com', 'inven.ai', 'top 22', 'top-22', 'yelp.com', 'angi.com', 'homeadvisor.com', 'thumbtack.com', 'bbb.org', 'facebook.com']

try:
    with open(new_leads_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        # print(f"Headers found: {headers}")
        
        for row in reader:
            # Map columns
            name = row.get('OSrXXb', '').strip()
            website = row.get('yYlJEf href', '').strip()
            phone = row.get('rllt__details 3', '').replace('· ', '').strip()
            
            if not name: continue
            
            # Dedup
            name_lower = name.lower()
            if name_lower in existing_names:
                continue
            
            domain = ""
            if website:
                try:
                    domain = urlparse(website).netloc.replace('www.', '').lower()
                except: pass
                
            if domain and (domain in existing_websites or domain in seen_current_batch):
                continue
                
            # Filter bad
            if website and any(bad in website.lower() for bad in bad_patterns):
                continue
                
            # Valid
            if domain: seen_current_batch.add(domain)
            existing_names.add(name_lower)
            
            new_leads.append({
                'business_name': name,
                'website': website,
                'phone': phone,
                'lead_score': 75,
                'source_query': 'Ohio Google Batch 2'
            })
            
except Exception as e:
    print(f"Error processing new file: {e}")
    sys.exit(1)

print(f"Found {len(new_leads)} unique new leads.")

# 3. Save
keys = ['business_name', 'website', 'email', 'email_tier', 'phone', 'lead_score', 'validation_signals', 'source_query', 'email_role', 'Email_Source']
try:
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for lead in new_leads:
            row = {k: lead.get(k, '') for k in keys}
            writer.writerow(row)
    print(f"Saved to {output_file}")
except Exception as e:
    print(f"Error saving: {e}")
    sys.exit(1)
