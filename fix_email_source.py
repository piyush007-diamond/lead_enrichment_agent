import csv

# Fix Email_Source to match corrected email_tier
input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

print("Fixing Email_Source to match tier...")
print("="*60)

changes = 0

for row in rows:
    email = row.get('email', '')
    tier = row.get('email_tier', '')
    role = row.get('email_role', '')
    old_source = row.get('Email_Source', '')
    
    if not email:
        continue
    
    # Set correct Email_Source based on tier and role
    if tier == '1' and role == 'owner':
        new_source = 'Tier 1 (Decision Maker)'
    elif tier == '2' and role == 'generic':
        new_source = 'Tier 2 (Generic)'
    elif tier == '3' and role == 'operational':
        new_source = 'Tier 3 (Operational)'
    else:
        new_source = 'Unknown'
    
    if old_source != new_source:
        row['Email_Source'] = new_source
        print(f"Fixed: {email}")
        print(f"  From: {old_source}")
        print(f"  To: {new_source}")
        changes += 1

# Save
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n{'='*60}")
print(f"Email_Source Correction Complete!")
print(f"Total Changes: {changes}")
print(f"Saved to: {output_file}")
