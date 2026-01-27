
import csv
import os
import sys
import logging

# Ensure execution module is in path
sys.path.append(os.getcwd())
from execution.enrich_google_leads import LeadEnricher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def super_clean_and_tier():
    base_dir = r"c:\Users\Piyush\Downloads\lead enreaching agent"
    input_file = os.path.join(base_dir, "smart_leads_HVAC_Arizona_enriched.csv")
    output_file = input_file # Overwrite in place
    
    if not os.path.exists(input_file):
        logging.error("File not found.")
        return

    enricher = LeadEnricher()
    
    cleaned_rows = []
    dropped_count = 0
    retiered_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        # Ensure email_role is in fieldnames
        if 'email_role' not in fieldnames:
            fieldnames.append('email_role')
            
        for row in reader:
            website = row.get('Website', '')
            email = row.get('Email_Primary', '')
            name = row.get('business_name', '')
            
            # 1. Business Ownership Gate (Hard Stop)
            is_valid_site = True
            if website:
                if not enricher.validate_business_site(website):
                    is_valid_site = False
                    logging.info(f"🛑 REJECTED [Directory/Bad]: {name} ({website})")
            
            # Also check name? (e.g. "Top 22 HVAC...")
            if "top 10" in name.lower() or "top 22" in name.lower() or "best hvac" in name.lower():
                 is_valid_site = False
                 logging.info(f"🛑 REJECTED [Bad Name]: {name}")

            if not is_valid_site:
                dropped_count += 1
                continue # DROP THE ROW ENTIRELY
            
            # 2. Re-Tiering Logic
            if email:
                tier_string, role = enricher.categorize_email_role(email)
                
                # Check if it changed (optimization)
                old_tier = row.get('Email_Source', '')
                old_role = row.get('email_role', '')
                
                # Update row
                row['Email_Source'] = tier_string
                row['email_role'] = role
                
                # Tier 3 Priority Check: "Never email operational first"
                # If we have a generic (Tier 2) or Owner (Tier 1), great.
                # If we only have Tier 3, we keep it but it will be low priority.
                # The user asked to "Adjust tiers so your scoring reflects decision power".
                # We have done that via categorize_email_role.
                
                if tier_string != old_tier:
                    # logging.info(f"   🔄 Re-Tiered {email}: {old_tier} -> {tier_string}")
                    retiered_count += 1
            else:
                row['email_role'] = 'none'

            cleaned_rows.append(row)

    # Save
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    logging.info(f"Super Clean Complete.")
    logging.info(f"Dropped {dropped_count} directory/spam rows.")
    logging.info(f"Re-Tiered {retiered_count} emails.")
    logging.info(f"Remaining Leads: {len(cleaned_rows)}")

if __name__ == "__main__":
    super_clean_and_tier()
