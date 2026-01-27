import csv

# Read the V2 enriched file
with open('smart_leads_HVAC_Ohio_ULTIMATE_V2.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

total_leads = len(rows)
batch2_leads = [r for r in rows if 'Batch 2' in r.get('source_query', '')]
b2_total = len(batch2_leads)

# Count owner names
b2_with_owner = [r for r in batch2_leads if r.get('owner_name')]
owner_count = len(b2_with_owner)

# Email confidence breakdown
confidence_counts = {}
for row in batch2_leads:
    conf = row.get('email_confidence_type', 'None')
    confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

print(f"Total Leads: {total_leads}")
print(f"Batch 2 Leads: {b2_total}")
print(f"Batch 2 with Owner Names: {owner_count} ({owner_count/b2_total*100:.1f}%)")
print()
print("Email Confidence Breakdown:")
for conf_type, count in sorted(confidence_counts.items()):
    print(f"  {conf_type}: {count} ({count/b2_total*100:.1f}%)")
print()
print("Sample Owner Names Found:")
for i, row in enumerate(b2_with_owner[:10], 1):
    print(f"  {i}. {row.get('owner_name')} ({row.get('name_source')})")
