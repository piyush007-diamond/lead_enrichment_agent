import csv

# Analyze Ohio leads for content pages
input_file = "smart_leads_HVAC_Ohio_enriched.csv"

bad_url_patterns = ['/blog/', '/about/', '/service-area/', '/news/', '/article/', 
                    '/residential-services/', '/commercial-services/', '/family-owned/',
                    '/air-filters/', '/our-team/', '/story/', '/sponsor-story/']

total = 0
bad_urls = []
good_urls = []

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        website = row.get('website', '').lower()
        name = row.get('business_name', '')
        
        total += 1
        is_bad = False
        
        # Check for content pages
        for pattern in bad_url_patterns:
            if pattern in website:
                bad_urls.append((name, website, pattern))
                is_bad = True
                break
        
        # Check for news domains
        if 'dispatch.com' in website or 'news' in website:
            bad_urls.append((name, website, 'news domain'))
            is_bad = True
            
        if not is_bad:
            good_urls.append((name, website))

impact_percent = (len(bad_urls) / total) * 100

print(f"📊 Ohio Leads Analysis")
print(f"=" * 60)
print(f"Total Leads: {total}")
print(f"Content Pages Found: {len(bad_urls)}")
print(f"Valid Business URLs: {len(good_urls)}")
print(f"Impact: {impact_percent:.1f}%")
print()

if bad_urls:
    print(f"🔍 Content Pages to Remove:")
    for name, url, pattern in bad_urls[:10]:  # Show first 10
        print(f"  - {name[:50]}")
        print(f"    URL: {url[:80]}")
        print(f"    Issue: {pattern}")
        print()

print(f"\n{'='*60}")
if impact_percent >= 20:
    print(f"✅ RECOMMEND: Apply Canonical URL Filter (Impact: {impact_percent:.1f}%)")
else:
    print(f"⚠️ SKIP: Impact too low ({impact_percent:.1f}% < 20%)")
