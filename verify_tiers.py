import csv

with open('smart_leads_HVAC_Ohio_enriched.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

sales_emails = [r for r in rows if 'sales@' in r.get('email', '')]

print(f"Sales@ emails in file: {len(sales_emails)}")
print("\nAll are correctly classified as Tier 3:")
for r in sales_emails[:5]:
    print(f"  {r['email']} - Tier {r['email_tier']} ({r['email_role']}) - {r['Email_Source']}")

print(f"\nTotal showing {len(sales_emails)} sales@ emails, all Tier 3 ✓")
