
import csv
import sys
import os

def analyze_quality(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    total_rows = 0
    rejected = 0
    with_email = 0
    with_phone = 0
    with_owner = 0
    email_sources = {}
    email_confidence_sum = 0
    email_count_for_avg = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            
            # Check rejection (Empty website usually means rejected by Business Gate)
            website = row.get('Website', '').strip()
            if not website:
                rejected += 1
                continue

            # Email Stats
            email = row.get('Email_Primary', '').strip()
            if email:
                with_email += 1
                # Source breakdown
                source = row.get('Email_Source', 'Unknown')
                email_sources[source] = email_sources.get(source, 0) + 1
                
                # Confidence
                try:
                    conf = float(row.get('Email_Confidence', 0))
                    email_confidence_sum += conf
                    email_count_for_avg += 1
                except:
                    pass

            # Phone Stats
            phone = row.get('Phone_Primary', '').strip()
            if phone:
                with_phone += 1

            # Owner Stats (Doctor_Name field used for Owner)
            owner = row.get('Doctor_Name', '').strip()
            if owner:
                with_owner += 1

    # Calculations
    valid_leads = total_rows - rejected
    enrichment_rate = (with_email / valid_leads * 100) if valid_leads > 0 else 0
    owner_rate = (with_owner / valid_leads * 100) if valid_leads > 0 else 0
    avg_confidence = (email_confidence_sum / email_count_for_avg) if email_count_for_avg > 0 else 0

    print(f"--- Lead Quality Analysis ---")
    print(f"Total Input Leads: {total_rows}")
    print(f"🚫 Rejected (Directories/Junk): {rejected} ({rejected/total_rows*100:.1f}%)")
    print(f"✅ Valid Businesses Processed: {valid_leads}")
    print(f"\n[ Enrichment Metrics ]")
    print(f"📧 Emails Found: {with_email} ({enrichment_rate:.1f}%)")
    print(f"📞 Phones Found: {with_phone} ({with_phone/valid_leads*100:.1f}%)")
    print(f"👤 Owners Identified: {with_owner} ({owner_rate:.1f}%)")
    print(f"⭐ Avg Email Confidence: {avg_confidence:.1f}/100")
    
    print(f"\n[ Email Sources ]")
    for source, count in email_sources.items():
        print(f"  - {source}: {count}")

if __name__ == "__main__":
    analyze_quality(r"c:\Users\Piyush\Downloads\lead enreaching agent\smart_leads_HVAC_Arizona_enriched.csv")
