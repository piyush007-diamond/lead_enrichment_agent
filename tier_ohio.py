import csv
import sys
sys.path.append('.')
from execution.enrich_google_leads import LeadEnricher

# Apply email tiering to Ohio leads
input_file = "smart_leads_HVAC_Ohio_clean.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

enricher = LeadEnricher()

rows = []
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    # Update fieldnames to include Email_Source if not present
    fieldnames = list(reader.fieldnames)
    if 'Email_Source' not in fieldnames:
        fieldnames.append('Email_Source')
    
    for row in reader:
        email = row.get('email', '')
        
        if email:
            # Apply tiering
            tier_string, role = enricher.categorize_email_role(email)
            row['Email_Source'] = tier_string
            row['email_role'] = role
        else:
            row['Email_Source'] = ''
            row['email_role'] = 'none'
            
        rows.append(row)

# Write output
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# Count tier distribution
tier_counts = {'owner': 0, 'generic': 0, 'operational': 0, 'none': 0}
for row in rows:
    tier_counts[row.get('email_role', 'none')] += 1

print(f"✅ Ohio leads enriched and tiered!")
print(f"📊 Distribution:")
print(f"   Tier 1 (Owner): {tier_counts['owner']} leads")
print(f"   Tier 2 (Generic): {tier_counts['generic']} leads")
print(f"   Tier 3 (Operational): {tier_counts['operational']} leads")
print(f"   No Email: {tier_counts['none']} leads")
print(f"   Total: {len(rows)} leads")
print(f"\n📁 Saved to: {output_file}")
