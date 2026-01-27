import csv
import sys

# Files
main_file = "smart_leads_HVAC_Ohio_enriched.csv"
batch2_file = "ohio_batch2_enriched.csv"

# Load Batch 2
try:
    with open(batch2_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch2_rows = list(reader)
except Exception as e:
    print(f"Error loading batch 2: {e}")
    sys.exit(1)
    
print(f"Loaded {len(batch2_rows)} leads from Batch 2.")

# Stats
added_emails = 0
tier1 = 0
tier3 = 0

for row in batch2_rows:
    if row.get('email'):
        added_emails += 1
        if row.get('email_tier') == '1': tier1 += 1
        else: tier3 += 1

print(f"Batch 2 Stats:")
print(f"  Total: {len(batch2_rows)}")
print(f"  Emails Found: {added_emails}")
print(f"  Tier 1: {tier1}")
print(f"  Tier 3: {tier3}")

# Merge
try:
    with open(main_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
        # Check if file needs header? No, it's 'a'ppend to existing file.
        # But we should ensure fieldnames match.
        # Assuming they do since we generated batch2 using same keys.
        writer.writerows(batch2_rows)
    print(f"Merged successfully into {main_file}")
except Exception as e:
    print(f"Error merging: {e}")
    sys.exit(1)
