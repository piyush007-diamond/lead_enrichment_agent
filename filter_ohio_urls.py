import csv

# Apply Canonical URL Filter to Ohio leads
input_file = "smart_leads_HVAC_Ohio_enriched.csv"
output_file = "smart_leads_HVAC_Ohio_enriched.csv"

bad_url_patterns = ['/blog/', '/about/', '/service-area/', '/news/', '/article/', 
                    '/residential-services/', '/commercial-services/', '/family-owned/',
                    '/air-filters/', '/our-team/', '/story/', '/sponsor-story/']

rows = []
removed = []

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    
    for row in reader:
        website = row.get('website', '').lower()
        name = row.get('business_name', '')
        
        keep = True
        
        # Check for content pages
        for pattern in bad_url_patterns:
            if pattern in website:
                removed.append(f"{name} ({pattern})")
                keep = False
                break
        
        # Check for news domains
        if keep and ('dispatch.com' in website or 'news' in website):
            removed.append(f"{name} (news domain)")
            keep = False
            
        if keep:
            rows.append(row)

# Write filtered data
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"🔧 Canonical URL Filter Applied")
print(f"=" * 60)
print(f"Removed: {len(removed)} content pages")
print(f"Remaining: {len(rows)} valid business leads")
print()

if removed:
    print("Removed:")
    for item in removed:
        print(f"  🔥 {item}")

print(f"\n✅ Clean data saved to: {output_file}")
