
import csv
import os

def final_scrub():
    base_dir = r"c:\Users\Piyush\Downloads\lead enreaching agent"
    input_file = os.path.join(base_dir, "smart_leads_HVAC_Arizona_enriched.csv")
    output_file = input_file
    
    if not os.path.exists(input_file):
        print("File not found.")
        return

    # HARD CODED BLOCKLISTS (The "Nuclear Option")
    BAD_DOMAINS = [
        'indiamart', 'trane', 'expertise', 'networx', 'yelp', 'angi', 
        'facebook', 'linkedin', 'instagram', 'youtube', 'twitter',
        'servicetitan', 'bbb.org', 'yellowpages', 'porch', 'thumbtack',
        'visitarizona', 'delhi.gov', 'jagranjosh', 'inven.ai', 'wiktionary',
        'reddit', 'en.wiktionary'
    ]
    
    BAD_KEYWORDS = [
        'marketplace', 'directory', 'dealer', 'find-a', 'top-', 'best-', 
        'guide', 'blog', 'poweredby', 'listing', 'licensing', 'top-10', 'best-of'
    ]
    
    cleaned_rows = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            website = row.get('Website', '').lower()
            name = row.get('business_name', '').lower()
            
            keep = True
            
            # 1. Check Domain
            if any(bad in website for bad in BAD_DOMAINS):
                print(f"🔥 BURNED [Domain]: {row['business_name']} ({website})")
                keep = False
                
            # 2. Check Keywords in URL
            if keep and any(bad in website for bad in BAD_KEYWORDS):
                print(f"🔥 BURNED [Keyword]: {row['business_name']} ({website})")
                keep = False
                
            # 3. Check Name
            if keep:
                if "top 22" in name or "license & certification" in name:
                     print(f"🔥 BURNED [Name]: {row['business_name']}")
                     keep = False

            if keep:
                cleaned_rows.append(row)

    # Save
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    print(f"Final Scrub Complete. {len(cleaned_rows)} valid leads remaining.")

if __name__ == "__main__":
    final_scrub()
