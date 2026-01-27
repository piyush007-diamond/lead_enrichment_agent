import csv

with open('smart_leads_HVAC_Ohio_ULTIMATE_V2.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

b2 = [x for x in rows if 'Batch 2' in x.get('source_query', '')]
no_email = [x for x in b2 if not x.get('email')]

print(f'Batch 2 total: {len(b2)}')
print(f'Batch 2 without email: {len(no_email)}')
print(f'With website: {len([x for x in no_email if x.get("website")])}')
print()
print('Sample without email:')
for x in no_email[:5]:
    print(f'  - {x.get("business_name")[:50]}')
    print(f'    Website: {x.get("website") or "NONE"}')
    print(f'    Email: {x.get("email") or "NONE"}')
