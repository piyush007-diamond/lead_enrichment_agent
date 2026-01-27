import csv

with open('smart_leads_HVAC_Ohio_enriched.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
print(f"Total Ohio Leads: {len(rows)}")
print()

# Count by email_role
roles = {}
for row in rows:
    role = row.get('email_role', 'none')
    roles[role] = roles.get(role, 0) + 1

print("Email Distribution:")
for role in ['owner', 'generic', 'operational', 'none']:
    count = roles.get(role, 0)
    if count > 0:
        print(f"  {role}: {count}")
