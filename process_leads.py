"""
Script to process google.csv and create filtered dentist leads for Arizona.

Filtering Criteria:
1. Filter for 100-500 Reviews (removes tiny clinics and giant corporate chains)
2. Remove Duplicates (based on business name)
3. Sort by "Busiest" First (highest reviews first within range)

Output: dentist.leads.arizona.csv
"""

import csv
import os
import re

# Input and output file paths
input_file = os.path.join(os.path.dirname(__file__), '..', 'google.csv')
output_file = os.path.join(os.path.dirname(__file__), 'dentist.leads.arizona.csv')

# Column mapping based on analysis
NAME_COL = 'OSrXXb'        # Business name
TYPE_COL = 'rllt__details'  # Type (e.g., "· Dentist")
RATING_COL = 'yi40Hd'       # Rating (e.g., "4.7")
REVIEWS_COL = 'RDApEe'      # Reviews count (e.g., "(1.3K)")
LOCATION_COL = 'rllt__details 2'  # Location
SERVICES_COL = 'BI0Dve'     # Services
IMAGE_COL = 'wA1Bge src'    # Image URL
QUOTE_COL = 'uDyWh'         # Customer quote

def parse_reviews(review_str):
    """
    Parse review count from strings like "(1.3K)", "(286)", "(2.5K)"
    Returns integer count or None if parsing fails
    """
    if not review_str:
        return None
    
    # Remove parentheses and whitespace
    clean = review_str.strip().replace('(', '').replace(')', '').strip()
    
    if not clean:
        return None
    
    try:
        # Handle 'K' suffix (thousands)
        if 'K' in clean.upper():
            # Extract the number and multiply by 1000
            num = float(clean.upper().replace('K', '').replace(',', ''))
            return int(num * 1000)
        else:
            # Regular number
            return int(float(clean.replace(',', '')))
    except (ValueError, TypeError):
        return None

def process_leads():
    print(f"Reading from: {os.path.abspath(input_file)}")
    
    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    
    print(f"Original records: {len(rows)}")
    
    # Step 1: Filter for 100-500 reviews
    filtered_rows = []
    review_stats = {'under_100': 0, 'in_range': 0, 'over_500': 0, 'invalid': 0}
    
    for row in rows:
        reviews = parse_reviews(row.get(REVIEWS_COL, ''))
        
        if reviews is None:
            review_stats['invalid'] += 1
            continue
        
        if reviews < 100:
            review_stats['under_100'] += 1
        elif reviews > 500:
            review_stats['over_500'] += 1
        else:
            review_stats['in_range'] += 1
            row['_reviews_numeric'] = reviews  # Store for sorting
            filtered_rows.append(row)
    
    print(f"\nReview Stats:")
    print(f"  Under 100 reviews (tiny clinics): {review_stats['under_100']}")
    print(f"  100-500 reviews (target range): {review_stats['in_range']}")
    print(f"  Over 500 reviews (corporate chains): {review_stats['over_500']}")
    print(f"  Invalid/missing reviews: {review_stats['invalid']}")
    print(f"\nAfter filtering 100-500 reviews: {len(filtered_rows)} records")
    
    # Step 2: Remove duplicates based on business name
    seen_names = set()
    deduped_rows = []
    duplicates_removed = 0
    
    for row in filtered_rows:
        name = row.get(NAME_COL, '').strip().lower()
        if name and name not in seen_names:
            seen_names.add(name)
            deduped_rows.append(row)
        else:
            duplicates_removed += 1
    
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"After removing duplicates: {len(deduped_rows)} records")
    
    # Step 3: Sort by "Busiest" first (highest reviews first within range)
    sorted_rows = sorted(deduped_rows, key=lambda x: x.get('_reviews_numeric', 0), reverse=True)
    print(f"Sorted by busiest (highest reviews) first")
    
    # Clean up temporary field and prepare final data
    for row in sorted_rows:
        if '_reviews_numeric' in row:
            del row['_reviews_numeric']
    
    # Save the result
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(sorted_rows)
    
    print(f"\n✅ Successfully created: {output_file}")
    print(f"Final record count: {len(sorted_rows)}")
    
    # Show top 5 leads
    print(f"\n=== Top 5 Leads (Busiest First) ===")
    for i, row in enumerate(sorted_rows[:5]):
        print(f"{i+1}. {row.get(NAME_COL)} - {row.get(REVIEWS_COL)} reviews - {row.get(LOCATION_COL)}")

if __name__ == "__main__":
    process_leads()
