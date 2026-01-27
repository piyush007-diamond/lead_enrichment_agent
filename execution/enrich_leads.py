"""
Script: enrich_leads.py
Purpose: Enrich dentist leads with website, email, and doctor name.
"""

import csv
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT_FILE = os.path.join(BASE_DIR, 'dentist.leads.arizona.csv')
OUTPUT_FILE = os.path.join(BASE_DIR, 'dentist.leads.arizona.enriched.csv')

# Headers for requests to look like a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def find_emails(text):
    # Basic email regex
    emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
    # Filter out common junk emails
    valid_emails = [e for e in emails if not any(x in e.lower() for x in ['wix', 'sentry', 'example', 'domain', 'email', 'png', 'jpg', 'svg'])]
    return ', '.join(valid_emails[:2]) if valid_emails else ''

def find_doctor_names(text):
    # Naive search for Dr. Name
    # Look for "Dr. First Last"
    matches = re.findall(r'Dr\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', text)
    unique_names = sorted(list(set(matches)))
    return ', '.join(unique_names[:3]) if unique_names else ''

def get_website_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        logging.warning(f"Failed to fetch {url}: {e}")
    return ""

def process_leads():
    if not os.path.exists(INPUT_FILE):
        logging.error(f"Input file not found: {INPUT_FILE}")
        return

    # Read input
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Add new columns including Website (which might not be in original if we are finding it)
    new_fields = fieldnames + ['Website', 'Enriched_Email', 'Enriched_Doctor_Name']
    
    enriched_rows = []
    
    logging.info(f"Starting enrichment for {len(rows)} leads...")

    try:
        for i, row in enumerate(rows):
            business_name = row.get('OSrXXb', '')
            location = row.get('rllt__details 2', '')
            
            logging.info(f"Processing {i+1}/{len(rows)}: {business_name}")
            website = row.get('Website', '')
            
            if not website:
                # Search for website using Google with conservative delay
                query = f"{business_name} {location} dentist site:*.com -site:yelp.com -site:facebook.com -site:healthgrades.com"
                try:
                    # Sleep before search to avoid 429
                    # Randomized delay 30-60s
                    delay = random.uniform(30, 60)
                    time.sleep(delay) 
                    
                    results = list(search(query, num_results=1, sleep_interval=5))
                    
                    for url in results:
                        # Filter junk
                        if any(x in url for x in ['yelp', 'facebook', 'healthgrades', 'mapquest', 'yellowpages', 'linkedin', '.gov', '.edu']):
                            continue
                        
                        # Use first valid result
                        website = url
                        logging.info(f"Reference found: {website}")
                        break
                except Exception as e:
                    logging.error(f"Search failed for {business_name}: {e}")
                    if "429" in str(e):
                         logging.warning("Hit 429, sleeping for 120s...")
                         time.sleep(120)

            email = ''
            doctor = ''
            
            if website:
                html = get_website_content(website)
                if html:
                    email = find_emails(html)
                    doctor = find_doctor_names(html)
                    
                    # If main page doesn't have info, try to find Contact/About/Team links
                    soup = BeautifulSoup(html, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link['href'].lower()
                        if any(x in href for x in ['contact', 'about', 'team', 'staff', 'doctor', 'our-team', 'meet-the-doctor']):
                            # Construct absolute URL
                            sub_url = link['href']
                            if not sub_url.startswith('http'):
                                if sub_url.startswith('/'):
                                    sub_url = website.rstrip('/') + sub_url
                                else:
                                    sub_url = website.rstrip('/') + '/' + sub_url
                            
                            # Fetch sub-page
                            sub_html = get_website_content(sub_url)
                            if sub_html:
                                # Append found info if not already found
                                new_emails = find_emails(sub_html)
                                new_doctors = find_doctor_names(sub_html)
                                if new_emails:
                                    if not email: email = new_emails
                                    elif new_emails not in email: email += ", " + new_emails
                                
                                if new_doctors:
                                    if not doctor: doctor = new_doctors
                                    elif new_doctors not in doctor: doctor += ", " + new_doctors
            
            # Update row
            row['Website'] = website
            row['Enriched_Email'] = email
            row['Enriched_Doctor_Name'] = doctor
            enriched_rows.append(row)
            
            # Intermediate save every 5 rows
            if (i + 1) % 5 == 0:
                logging.info("Saving checkpoint...")
                with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f_out:
                    writer = csv.DictWriter(f_out, fieldnames=new_fields)
                    writer.writeheader()
                    writer.writerows(enriched_rows)

    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Saving current progress...")
    
    # Final save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(enriched_rows)
    
    logging.info(f"Enrichment complete. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_leads()
