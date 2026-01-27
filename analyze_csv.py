"""
Script to analyze google.csv structure and save to file
"""

import csv
import os

# Input file path
input_file = os.path.join(os.path.dirname(__file__), '..', 'google.csv')
output_file = os.path.join(os.path.dirname(__file__), 'csv_analysis.txt')

def analyze_csv():
    lines = []
    lines.append(f"Reading from: {os.path.abspath(input_file)}\n")
    
    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        all_rows = list(reader)
    
    lines.append(f"\nTotal rows (including header): {len(all_rows)}\n")
    lines.append(f"\n=== First 5 rows (raw) ===\n")
    for i, row in enumerate(all_rows[:5]):
        lines.append(f"Row {i}: {row}\n")
    
    lines.append(f"\n=== Column Analysis ===\n")
    if all_rows:
        header = all_rows[0]
        lines.append(f"Number of columns: {len(header)}\n")
        for i, col in enumerate(header):
            lines.append(f"  Column {i}: '{col}'\n")
            # Show sample values from this column
            sample_values = [all_rows[j][i] if i < len(all_rows[j]) else 'N/A' 
                           for j in range(1, min(6, len(all_rows)))]
            for j, val in enumerate(sample_values):
                lines.append(f"    Row {j+1}: {val[:100]}...\n" if len(val) > 100 else f"    Row {j+1}: {val}\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Analysis saved to: {output_file}")

if __name__ == "__main__":
    analyze_csv()
