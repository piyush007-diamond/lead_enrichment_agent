"""
Script: validate_data.py
Purpose: Validate doctor credentials via NPI Registry and verify email domains.
"""

import csv
import os
import requests
import time
import logging
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT_FILE = os.path.join(BASE_DIR, 'dentist.leads.arizona.enriched.csv')
OUTPUT_FILE = os.path.join(BASE_DIR, 'dentist.leads.arizona.verified.csv')

# NPI API Endpoint
NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"
NPI_VERSION = "2.1"

def get_domain(url):
    """Extract domain from URL (e.g. https://www.site.com/foo -> site.com)"""
    if not url: return ""
    if not url.startswith('http'): url = 'http://' + url
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith('www.'): netloc = netloc[4:]
        return netloc.lower()
    except:
        return ""

def check_npi(first_name, last_name, state='AZ'):
    """Query NPPES API for a dentist"""
    if not first_name or not last_name:
        return None
    
    params = {
        'first_name': first_name,
        'last_name': last_name,
        'state': state,
        'taxonomy_description': 'Dentist',
        'version': NPI_VERSION
    }
    
    try:
        response = requests.get(NPI_API_URL, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('result_count', 0) > 0:
                # Return the first match's NPI number and basic info
                provider = data['results'][0]
                return {
                    'number': provider['number'],
                    'status': provider['basic']['status'],
                    'name': f"{provider['basic']['first_name']} {provider['basic']['last_name']}"
                }
    except Exception as e:
        logging.warning(f"NPI Check failed for {first_name} {last_name}: {e}")
    
    return None

def process_validation():
    if not os.path.exists(INPUT_FILE):
        logging.error(f"Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    new_fields = fieldnames + ['NPI_Number', 'NPI_Status', 'Email_Validation', 'Quality_Score']
    verified_rows = []

    logging.info(f"Validating {len(rows)} leads...")

    for i, row in enumerate(rows):
        # 1. Parse Doctor Name
        raw_name = row.get('Enriched_Doctor_Name', '')
        # Handle multiple names (take first usually, or split if comma)
        if ',' in raw_name:
            # "Dr. A, Dr. B" -> take "Dr. A"
            raw_name = raw_name.split(',')[0].strip()
        
        # Remove "Dr." prefix
        clean_name = raw_name.replace('Dr.', '').replace('DDS', '').replace('DMD', '').strip()
        parts = clean_name.split()
        
        npi_data = None
        if len(parts) >= 2:
            first = parts[0]
            last = parts[-1]
            npi_data = check_npi(first, last)
            # Sleep slightly to handle rate limiting if any (NPI is generous but good practice)
            time.sleep(0.5)
        
        # 2. Update NPI columns
        if npi_data:
            row['NPI_Number'] = npi_data['number']
            row['NPI_Status'] = npi_data['status']
            logging.info(f"NPI MATCH: {clean_name} -> {npi_data['number']}")
        else:
            row['NPI_Number'] = ''
            row['NPI_Status'] = 'Not Found'

        # 3. Validate Email
        website = row.get('Website', '')
        email = row.get('Enriched_Email', '')
        if ',' in email: email = email.split(',')[0].strip() # Check first email

        web_domain = get_domain(website)
        email_domain = email.split('@')[-1].lower() if '@' in email else ""
        
        validation_status = "Missing"
        if email:
            if email_domain == web_domain and web_domain:
                validation_status = "Domain Match"
            elif any(x in email_domain for x in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol']):
                validation_status = "Generic Provider"
            else:
                validation_status = "Domain Mismatch"
        
        row['Email_Validation'] = validation_status

        # 4. Score Quality
        # High: NPI Found + (Domain Match OR Generic) -> We know the doctor exists
        # Medium: NPI Found OR Domain Match
        # Low: Neither
        score = "Low"
        if row['NPI_Status'] == 'A': # Active
            if validation_status in ['Domain Match', 'Generic Provider']:
                score = "High"
            else:
                score = "Medium"
        elif validation_status == 'Domain Match':
            score = "Medium"
        
        row['Quality_Score'] = score
        verified_rows.append(row)

        if (i+1) % 10 == 0:
            logging.info(f"Processed {i+1} rows...")

    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(verified_rows)

    logging.info(f"Validation complete. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_validation()
