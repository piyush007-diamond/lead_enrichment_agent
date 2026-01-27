import csv
import os

# Quick clean of Ohio leads - remove directories
input_file = "smart_leads_HVAC_Ohio.csv"
output_file = "smart_leads_HVAC_Ohio_clean.csv"

bad_patterns = ['trane.com', 'find-a-dealer', 'servicetitan', 'expertise.com', 'networx.com', 'inven.ai', 'top 22', 'top-22']

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames) + ['email_role']  # Add email_role to headers
    rows = []
    
    for row in reader:
        website = row.get('website', '').lower()
        name = row.get('business_name', '').lower()
        
        keep = True
        # Check website
        if any(bad in website for bad in bad_patterns):
            print(f"🔥 Removed (bad website): {row['business_name']}")
            keep = False
        # Check business name  
        elif any(bad in name for bad in ['top 22', 'license & certification']):
            print(f"🔥 Removed (bad name): {row['business_name']}")
            keep = False
            
        if keep:
            row['email_role'] = 'none'  # Initialize email_role
            rows.append(row)

# Write cleaned data
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✅ Cleaned! {len(rows)} valid leads remaining (removed {54 - len(rows)} directories)")
