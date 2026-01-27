"""
Master Workflow Script
Executes lead enrichment for a specific niche profile.
Usage: python execution/run_workflow.py --profile <profile_name>
"""

import argparse
import json
import os
import sys
import logging
# Ensure we can import from execution module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.enrich_google_leads import LeadEnricher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_PATH = os.path.join(BASE_DIR, 'profiles.json')

def load_profile(profile_name):
    """Load configuration for the specified profile."""
    if not os.path.exists(PROFILES_PATH):
        logging.error(f"Profiles file not found at {PROFILES_PATH}")
        sys.exit(1)
        
    with open(PROFILES_PATH, 'r') as f:
        profiles = json.load(f)
        
    if profile_name not in profiles:
        logging.error(f"Profile '{profile_name}' not found. Available: {list(profiles.keys())}")
        sys.exit(1)
        
    return profiles[profile_name]

def main():
    parser = argparse.ArgumentParser(description='Run lead enrichment workflow')
    parser.add_argument('--profile', type=str, required=True, help='Profile name (e.g., dentist, hvac)')
    args = parser.parse_args()
    
    profile_name = args.profile.lower()
    logging.info(f"Starting workflow for profile: {profile_name}")
    
    config = load_profile(profile_name)
    
    # Resolve file paths
    input_file = os.path.join(BASE_DIR, config.get('input_file', 'google.csv'))
    output_file = os.path.join(BASE_DIR, config.get('output_file', f'{profile_name}_enriched.csv'))
    
    if not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        logging.info("Please ensure the input CSV file exists in the project root.")
        sys.exit(1)
        
    logging.info(f"Input: {input_file}")
    logging.info(f"Output: {output_file}")
    logging.info(f"Keywords: {config.get('keyword')}")
    
    # Initialize and run enricher with config
    enricher = LeadEnricher(config, input_file, output_file)
    enricher.process_leads()

if __name__ == "__main__":
    main()
