
import csv
import os

INPUT_FILE = r"C:\Users\Piyush\Downloads\lead enreaching agent\leads_HVAC_Arizona.csv"
OUTPUT_LOG = r"C:\Users\Piyush\Downloads\lead enreaching agent\debug_output.txt"

def debug_csv():
    with open(OUTPUT_LOG, 'w', encoding='utf-8') as log:
        log.write(f"Reading: {INPUT_FILE}\n")
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                log.write(f"Raw Fieldnames: {headers}\n")
                if headers:
                    log.write(f"Stripped Fieldnames: {[h.strip() for h in headers]}\n")
                
                log.write("\nFirst 5 rows:\n")
                for i, row in enumerate(reader):
                    if i >= 5: break
                    log.write(f"Row {i+1}: {row}\n")
                    log.write(f"Business Name (raw lookup): '{row.get('Business Name', 'NOT FOUND')}'\n")
                    # Try stripped lookup
                    stripped_lookup = 'NOT FOUND'
                    for k, v in row.items():
                        if k and k.strip() == 'Business Name':
                            stripped_lookup = v
                            break
                    log.write(f"Business Name (stripped lookup): '{stripped_lookup}'\n")
                    
        except Exception as e:
            log.write(f"Error: {e}\n")

if __name__ == "__main__":
    debug_csv()
