import csv

with open('smart_leads_HVAC_Ohio_V4_COMPLETE.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

b2 = [x for x in rows if 'Batch 2' in x.get('source_query', '')]
total = len(b2)

with_email = [x for x in b2 if x.get('email')]
email_count = len(with_email)

# V4 specific
v4_enriched = [x for x in b2 if x.get('Email_Source', '').startswith('V4_')]
v4_count = len(v4_enriched)

# Confidence breakdown
conf_counts = {}
for row in b2:
    conf = row.get('email_confidence_type', 'None')
    conf_counts[conf] = conf_counts.get(conf, 0) + 1

print(f"=" * 70)
print("FINAL BATCH 2 ENRICHMENT RESULTS")
print(f"=" * 70)
print(f"\nTotal Batch 2 Leads: {total}")
print(f"Leads with Emails: {email_count} ({email_count/total*100:.1f}%)")
print(f"  - V2 Enrichment: {email_count - v4_count}")
print(f"  - V4 Enrichment: {v4_count}")
print()
print("Email Confidence Breakdown:")
for conf, count in sorted(conf_counts.items()):
    print(f"  {conf}: {count} ({count/total*100:.1f}%)")
print()
print("V4 Success Details:")
for row in v4_enriched[:10]:
    print(f"  - {row['business_name'][:40]}")
    print(f"    Email: {row['email']}")
    print(f"    Source: {row['Email_Source']}")
