
import csv
import os
import sys
import logging

# Ensure execution module is in path
sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def full_enrichment_upgrade():
    base_dir = r"c:\Users\Piyush\Downloads\lead enreaching agent"
    enriched_file = os.path.join(base_dir, "smart_leads_HVAC_Arizona_enriched.csv")
    input_file_source = os.path.join(base_dir, "smart_leads_HVAC_Arizona.csv")
    
    if not os.path.exists(enriched_file):
        logging.error("Enriched file not found.")
        return

    # Load Source Data 
    source_map = {}
    if os.path.exists(input_file_source):
        with open(input_file_source, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_map[row['business_name']] = row

    # Load Enriched Data
    rows = []
    fieldnames = []
    with open(enriched_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    logging.info(f"Loaded {len(rows)} leads. Starting Full Upgrade Strategy.")

    enricher = LeadEnricher(config={"keyword": "hvac"})

    processed_count = 0
    upgraded_count = 0
    
    with open(enriched_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            name = row.get('business_name', '')
            processed_count += 1
            logging.info(f"[{processed_count}/{len(rows)}] Upgrading: {name}")
            
            source_row = source_map.get(name, row)
            
            try:
                # Run the new enrichment logic
                new_data = enricher.enrich_lead(source_row)
                
                # Merge Logic: We want to Keep the BEST data
                # 1. Anti-Directory: If new logic says "Skipped", we trust it?
                # Actually, validate_business_site is called inside enrich_lead.
                # If it rejected the site, new_data won't have scraped info.
                
                # 2. Owner Hunt / Social Rescue
                # We check if new_data has a BETTER email
                
                old_email = row.get('Email_Primary', '')
                old_tier = row.get('Email_Source', '')
                
                new_email = new_data.get('Email_Primary', '')
                new_tier = new_data.get('Email_Source', '')
                
                replacement = False
                
                if new_email and not old_email:
                    replacement = True # Filled a gap
                elif new_email and "Tier 1" in new_tier and "Tier 1" not in old_tier:
                     replacement = True # Upgrade to Owner
                elif new_email and "Tier 2" in new_tier and "Tier" not in old_tier and old_email:
                     # Maybe? No, generic website might be better than Social.
                     pass 
                
                if replacement:
                    logging.info(f"   ✨ UPGRADE: {old_email} ({old_tier}) -> {new_email} ({new_tier})")
                    row['Email_Primary'] = new_email
                    row['Email_Source'] = new_tier
                    row['Email_Confidence'] = new_data.get('Email_Confidence', '')
                    if new_data.get('email_role'):
                        row['email_role'] = new_data['email_role']
                    if new_data.get('Doctor_Name'):
                        row['Doctor_Name'] = new_data['Doctor_Name']
                    upgraded_count += 1
                
                # Always take new phone if missing
                if new_data.get('Phone_Primary') and not row.get('Phone_Primary'):
                     row['Phone_Primary'] = new_data['Phone_Primary']
                     row['Phone_Validated'] = new_data['Phone_Validated']
                     row['Phone_Source'] = new_data['Phone_Source']
                
                # Update website if we found one where there was none
                if new_data.get('Website') and not row.get('Website'):
                    row['Website'] = new_data['Website']
                    
            except Exception as e:
                logging.error(f"Error upgrading {name}: {e}")
            
            writer.writerow(row)
            f.flush()

    logging.info(f"Upgrade complete. Improved {upgraded_count} leads.")

if __name__ == "__main__":
    full_enrichment_upgrade()
