import csv

input_file = r"c:\Users\Piyush\Downloads\lead enreaching agent\smart_leads_HVAC_Arizona_enriched.csv"

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = [r for r in reader if 'Trane' not in r.get('business_name', '')]

with open(input_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Removed Trane. {len(rows)} leads remaining.")
