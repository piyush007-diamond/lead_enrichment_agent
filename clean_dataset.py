
import csv
import os
import sys
from urllib.parse import urlparse
# Add current dir to path to import LeadEnricher
sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher

def clean_dataset():
    input_file = r"c:\Users\Piyush\Downloads\lead enreaching agent\smart_leads_HVAC_Arizona_enriched.csv"
    output_file = input_file # Overwrite or create new? Overwrite is risky but requested fix. I'll overwrite.
    
    if not os.path.exists(input_file):
        print("File not found.")
        return

    enricher = LeadEnricher()
    
    cleaned_rows = []
    fieldnames = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            website = row.get('Website', '')
            email = row.get('Email_Primary', '')
            phone = row.get('Phone_Primary', '')
            business_name = row.get('business_name', 'Unknown')
            
            # 1. Email Check (Domain Lock)
            if email:
                domain = ""
                if website:
                    try:
                        domain = urlparse(website).netloc.replace('www.', '')
                    except: pass
                
                # Check validity using the new strict rule
                if not enricher.is_valid_lead(email, domain):
                    print(f"🚫 [Email] Removed bad email for {business_name}: {email} (Domain: {domain})")
                    row['Email_Primary'] = ''
                    row['Email_Confidence'] = '0'
                    row['Email_Source'] = ''
            
            # 2. Phone Check (Scam Blocker)
            if phone:
                # The enricher.is_fake_number checks for substrings like "666", "555"
                if enricher.is_fake_number(phone):
                    print(f"🚫 [Phone] Removed fake phone for {business_name}: {phone}")
                    row['Phone_Primary'] = ''
                    row['Phone_Validated'] = 'False'
                    row['Phone_Source'] = ''
            
            # Cleanup potential extra fields that DictReader captures as None due to header mismatch
            if None in row:
                del row[None]
            
            cleaned_rows.append(row)

    # Ensure all fieldnames from rows are included if feasible, or just stick to original header
    # If we want to keep Scrape Status but it wasn't in header:
    # check if any row has keys not in fieldnames
    all_keys = set().union(*(d.keys() for d in cleaned_rows))
    fieldnames = list(all_keys) # Re-build header to include everything found
    
    # Sort for consistency if possible, or just keep main ones first
    priority = ['business_name', 'Website', 'Email_Primary']
    fieldnames.sort(key=lambda x: priority.index(x) if x in priority else 999)

    # Save back
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    print(f"Done. Cleaned {len(cleaned_rows)} rows.")

if __name__ == "__main__":
    clean_dataset()
