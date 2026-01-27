# Directive: Enrich Google Dentist Leads (Multi-Strategy)

## Objective
Enrich the Google dentist leads data (`google.csv`) with **validated** email addresses and phone numbers using multiple enrichment strategies prioritized by reliability.

## Input File
- **File**: `C:\Users\Piyush\Downloads\google.csv`
- **Key Columns**:
  - `OSrXXb` - Business Name
  - `rllt__details 2` - Location (City, State)
  - `yi40Hd` - Rating
  - `RDApEe` - Review Count
  - `BI0Dve` - Services (e.g., "On-site services")

## Enrichment Strategy Priority

### Strategy 1: Website Scraping (Primary)
1. **Search for Official Website**
   - Query: `"{Business Name}" "{Location}" dentist official website -yelp -facebook -healthgrades`
   - Use DuckDuckGo or custom search to avoid rate limits
   - Verify domain legitimacy (check SSL, WHOIS if needed)

2. **Extract Contact Info**
   - **Email**: Multiple patterns
     - `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
     - Filter out: generic emails (info@wix.com, example@, etc.)
     - Prioritize: contact@, info@, appointments@, [doctorname]@
   
   - **Phone**: US format
     - `\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}`
     - Validate format and area code
   
   - **Doctor Names**: 
     - Pattern: `Dr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)`
     - Alternative: Look for DDS, DMD, D.M.D titles

3. **Search Multiple Pages**
   - Priority pages: Contact, About, Team/Staff, Our Doctors
   - Extract from footer sections
   - Check schema.org markup if available

### Strategy 2: Google Places API (Secondary)
- Extract official phone numbers from Google Places
- Verify business hours and status
- Get verified business information

### Strategy 3: Email Pattern Recognition + Verification
1. **Generate likely patterns**:
   ```
   {info, contact, appointments, reception, office}@{domain}
   ```
2. **Verify using**:
   - SMTP validation (check if mailbox exists)
   - DNS MX record lookup
   - Disposable email detection

### Strategy 4: Professional Directory Mining
- Search: Healthgrades, Zocdoc, ADA directory
- Cross-reference by name + location
- Extract verified contact information

## Data Quality Scoring

Assign confidence scores based on source:
- **Website Direct** = 95% confidence
- **Google Places API** = 90% confidence  
- **Directory Match** = 85% confidence
- **Pattern + SMTP Verified** = 75% confidence
- **Pattern Only** = 50% confidence

## Output Format

Create: `google_leads_enriched.csv`

Columns:
- All original columns from `google.csv`
- `Website` - Official website URL
- `Email_Primary` - Main email address
- `Email_Confidence` - Confidence score (0-100)
- `Email_Source` - How email was obtained
- `Phone_Primary` - Main phone number
- `Phone_Validated` - Boolean (True if format validated)
- `Phone_Source` - Source of phone number
- `Doctor_Name` - Primary dentist name(s)
- `Last_Updated` - Timestamp of enrichment

## Prioritization Logic

Process leads in this order:
1. Rating ≥ 4.8 AND Reviews ≥ 500 (High-value practices)
2. Rating ≥ 4.7 AND Reviews ≥ 200 (Medium-value)
3. "On-site services" = True (Active, mobile practices)
4. All others by review count descending

## Error Handling & Resilience

1. **Rate Limiting**
   - Random delay: 2-5 seconds between requests
   - Exponential backoff on 429 errors
   - Rotate user agents

2. **Save Progress**
   - Write to `.tmp/google_enrichment_progress.json` every 10 records
   - Allow resume from last processed position

3. **Error Logging**
   - Log to `.tmp/enrichment_errors.log`
   - Categories: SEARCH_FAIL, SCRAPE_FAIL, VALIDATION_FAIL, API_ERROR

4. **Validation**
   - Phone: Must match US format, valid area code
   - Email: Must have valid domain, MX record
   - Website: Must return 200 status, have SSL

## Performance Targets

- **Speed**: ~30-60 seconds per lead (with all strategies)
- **Success Rate**: 
  - Phone: ≥ 85% of leads
  - Email: ≥ 70% of leads  
  - Both: ≥ 65% of leads

## Required Dependencies

```python
# Install if missing:
pip install requests beautifulsoup4 duckduckgo-search dnspython phonenumbers validate-email-address
```

## API Keys Needed (Optional but Recommended)

- Google Places API key (for Strategy 2)
- Hunter.io API key (for email verification)
- EmailHippo or similar (for SMTP validation)

## Usage

```bash
python execution/enrich_google_leads.py
```
