import csv

input_file = r"c:\Users\Piyush\Downloads\lead enreaching agent\smart_leads_HVAC_Arizona_enriched.csv"

# Read all rows
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    all_rows = list(reader)

# Filter out bad domains
bad_patterns = ['trane.com', 'find-a-dealer', 'servicetitan', 'expertise.com', 'networx.com', 'inven.ai']
clean_rows = []

for row in all_rows:
    website = row.get('Website', '').lower()
    keep = True
    for bad in bad_patterns:
        if bad in website:
            print(f"Removing: {row['business_name']}")
            keep = False
            break
    if keep:
        clean_rows.append(row)

# Write back
with open(input_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(clean_rows)

print(f"Done. {len(clean_rows)} leads remaining (removed {len(all_rows) - len(clean_rows)}).")
