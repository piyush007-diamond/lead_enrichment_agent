
import csv
import os
import sys
import logging

# Ensure execution module is in path
sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def reprocess_gaps():
    base_dir = r"c:\Users\Piyush\Downloads\lead enreaching agent"
    enriched_file = os.path.join(base_dir, "smart_leads_HVAC_Arizona_enriched.csv")
    input_file_source = os.path.join(base_dir, "smart_leads_HVAC_Arizona.csv")
    
    if not os.path.exists(enriched_file):
        logging.error("Enriched file not found.")
        return

    # Load Source Data to get original queries/contexts if needed
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

    logging.info(f"Loaded {len(rows)} leads. Checking for gaps...")

    # Initialize Enricher
    enricher = LeadEnricher(config={
        "keyword": "hvac",
        # Use existing logic from profile if we loaded it, but default is fine for hvac
        "priority_keywords": ["emergency", "24/7", "repair"],
         "columns": {
          "name": "business_name",
          "location": "source_query",
          "rating": "lead_score",
          "reviews": "lead_score",
          "services": "validation_signals"
        }
    })

    reprocessed_count = 0
    
    with open(enriched_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            name = row.get('business_name', '')
            email = row.get('Email_Primary', '')
            phone = row.get('Phone_Primary', '')
            website = row.get('Website', '')
            
            # Criteria for re-processing: Missing Email OR Missing Phone
            # AND we have the source data to retry
            if (not email or not phone) and name in source_map:
                 logging.info(f"♻️ Reprocessing gap for: {name} (Missing: {'Email ' if not email else ''}{'Phone ' if not phone else ''})")
                 
                 # Get original source row
                 source_row = source_map[name]
                 # Enrich again
                 try:
                     # Add delay to be safe
                     enricher.rate_limit_delay()
                     
                     new_data = enricher.enrich_lead(source_row)
                     
                     # Be careful not to overwrite valid existing data if the new run fails
                     # But new run has "Domain Lock", so if it finds nothing, it returns nothing.
                     # We merge carefully: Only overwrite if new data is found, OR if old data was empty.
                     
                     if new_data.get('Email_Primary'):
                         row['Email_Primary'] = new_data['Email_Primary']
                         row['Email_Confidence'] = new_data['Email_Confidence']
                         row['Email_Source'] = new_data['Email_Source']
                         row['Doctor_Name'] = new_data['Doctor_Name'] # Update owner too
                     
                     if new_data.get('Phone_Primary'):
                         row['Phone_Primary'] = new_data['Phone_Primary']
                         row['Phone_Validated'] = new_data['Phone_Validated']
                         row['Phone_Source'] = new_data['Phone_Source']
                         
                     if new_data.get('Website') and not row.get('Website'):
                         row['Website'] = new_data['Website']
                         
                     reprocessed_count += 1
                     
                 except Exception as e:
                     logging.error(f"Error reprocessing {name}: {e}")
            
            writer.writerow(row)
            f.flush()

    logging.info(f"Reprocessing complete. Updated {reprocessed_count} rows.")

if __name__ == "__main__":
    reprocess_gaps()
