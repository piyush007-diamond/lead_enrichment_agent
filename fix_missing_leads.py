
import csv
import os
import sys
import logging
from execution.enrich_google_leads import LeadEnricher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_leads():
    base_dir = r"c:\Users\Piyush\Downloads\lead enreaching agent"
    input_file = os.path.join(base_dir, "smart_leads_HVAC_Arizona.csv")
    output_file = os.path.join(base_dir, "smart_leads_HVAC_Arizona_enriched.csv")
    
    # Load processed names
    processed_names = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('business_name'):
                    processed_names.add(row['business_name'])
    
    logging.info(f"Found {len(processed_names)} already processed leads.")
    
    # Load all input leads
    leads_to_process = []
    fieldnames = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row['business_name'] not in processed_names:
                leads_to_process.append(row)
    
    logging.info(f"Found {len(leads_to_process)} leads remaining to process.")
    
    if not leads_to_process:
        logging.info("All done!")
        return

    # Initialize Enricher
    enricher = LeadEnricher(config={
        "keyword": "hvac",
        "input_file": "smart_leads_HVAC_Arizona.csv", # Dummy
        "output_file": "smart_leads_HVAC_Arizona_enriched.csv", # Dummy
        "filter_min_reviews": 10,
        "filter_max_reviews": 5000,
        "contact_title_pattern": "(?:Technician|Manager|Owner)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)",
        "priority_keywords": ["emergency", "24/7", "repair"],
        "columns": {
          "name": "business_name",
          "location": "source_query",
          "rating": "lead_score",
          "reviews": "lead_score",
          "services": "validation_signals"
        }
    })
    
    # Prepare output header if file needs it (it shouldn't if we are appending, but ensure columns match)
    # We will append.
    
    # Define output columns (same as main script)
    new_columns = [
        'Website', 'Email_Primary', 'Email_Confidence', 'Email_Source',
        'Phone_Primary', 'Phone_Validated', 'Phone_Source',
        'Doctor_Name', 'Last_Updated', 'Scrape Status'
    ]
    output_fieldnames = list(fieldnames) + [c for c in new_columns if c not in fieldnames]

    # Process and Append
    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        # Note: No writeheader since file exists
        
        for i, row in enumerate(leads_to_process):
            logging.info(f"Processing remaining lead {i+1}/{len(leads_to_process)}: {row['business_name']}")
            try:
                enriched_data = enricher.enrich_lead(row)
            except Exception as e:
                logging.error(f"Error processing {row['business_name']}: {e}")
                enriched_data = {'Scrape Status': f'Error: {e}'}
            
            enriched_row = {**row, **enriched_data}
            writer.writerow(enriched_row)
            f.flush() # Ensure it's on disk!
            
    logging.info("Fix complete.")

if __name__ == "__main__":
    fix_leads()
