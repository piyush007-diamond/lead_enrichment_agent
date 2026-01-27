import csv
import re

# Correct Email Tiering per user specification
input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

print("Correcting Email Tiers...")
print("="*60)

changes = 0

for row in rows:
    email = row.get('email', '')
    if not email:
        continue
    
    local_part = email.split('@')[0].lower()
    
    # Tier 3 (Operational/Generic Business)
    tier3_keywords = ['info', 'contact', 'sales', 'support', 'service', 
                      'customerservice', 'billing', 'help', 'inquiry']
    
    # Tier 2 (Admin/General)
    tier2_keywords = ['admin', 'hello', 'office']
    
    # Tier 1 (Personal/Owner) - ONLY if it looks like a personal name
    # Must NOT contain any generic keywords
    is_personal = False
    
    # Check if it's NOT a generic keyword
    if not any(keyword in local_part for keyword in tier3_keywords + tier2_keywords):
        # Additional check: does it look like a name?
        # Names typically: firstname@, firstname.lastname@, firstinitiallastname@
        # And NOT: generic words like 'office', 'team', etc.
        
        # Simple heuristic: if local part is short (3-15 chars) and doesn't contain numbers
        if 2 <= len(local_part) <= 15 and not re.search(r'\d{2,}', local_part):
            # Could be a personal name
            is_personal = True
    
    old_tier = row.get('email_tier', '')
    old_role = row.get('email_role', '')
    
    # Assign tier
    if any(keyword in local_part for keyword in tier3_keywords):
        row['email_tier'] = '3'
        row['email_role'] = 'operational'
        tier_name = 'Tier 3 (Operational)'
    elif any(keyword in local_part for keyword in tier2_keywords):
        row['email_tier'] = '2'
        row['email_role'] = 'generic'
        tier_name = 'Tier 2 (Generic)'
    elif is_personal:
        row['email_tier'] = '1'
        row['email_role'] = 'owner'
        tier_name = 'Tier 1 (Personal/Owner)'
    else:
        # Default to Tier 3 if unsure
        row['email_tier'] = '3'
        row['email_role'] = 'operational'
        tier_name = 'Tier 3 (Operational)'
    
    if old_tier != row['email_tier']:
        print(f"Changed: {email}")
        print(f"  From: Tier {old_tier} ({old_role})")
        print(f"  To: Tier {row['email_tier']} ({row['email_role']})")
        changes += 1

# Save
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n{'='*60}")
print(f"Correction Complete!")
print(f"Total Changes: {changes}")

# Count final distribution
tier_counts = {'1': 0, '2': 0, '3': 0, 'none': 0}
for row in rows:
    tier = row.get('email_tier', 'none')
    tier_counts[tier] = tier_counts.get(tier, 0) + 1

print(f"\nFinal Distribution:")
print(f"  Tier 1 (Personal/Owner): {tier_counts.get('1', 0)} leads")
print(f"  Tier 2 (Generic): {tier_counts.get('2', 0)} leads")
print(f"  Tier 3 (Operational): {tier_counts.get('3', 0)} leads")
print(f"  No Email: {tier_counts.get('none', 0)} leads")
print(f"\nSaved to: {output_file}")
