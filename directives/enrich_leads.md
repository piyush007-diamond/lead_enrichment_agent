# Directive: Enrich Dentist Leads

## Objective
Enrich the existing `dentist.leads.arizona.csv` with contact information (Email, Phone) and Key Personnel (Doctor/Owner Name) by identifying the business website and scraping publicly available information.

## Inputs
- **Input File**: `dentist.leads.arizona.csv`
- **Columns to Use**:
    - `OSrXXb` (Business Name)
    - `rllt__details 2` (Location)

## Execution Process
1. **Load Data**: Read the input CSV.
2. **Search**: For each business, perform a web search to find the official website.
    - Query: `"{Business Name}" "{Location}" dentist site:*.com -site:yelp.com -site:facebook.com`
    - Logic: Take the first non-directory result.
3. **Scrape**: Visit the identified URL.
    - **Timeout**: Set a reasonable timeout (e.g., 10s) to avoid hanging.
    - **Target Pages**: If "Main" page doesn't have info, look for links to "Contact", "About", "Team", "Staff".
4. **Extract**:
    - **Email**: Regex match `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`.
    - **Phone**: Regex match `\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}` (if column is missing/empty).
    - **Doctor Name**: Look for "Dr. [Name]" or "DDS", "DMD" patterns.
5. **Output**:
    - Create a new CSV `dentist.leads.arizona.enriched.csv` with columns: `Business Name`, `Website`, `Email`, `Phone`, `Doctor Name`, `Source URL`.
    - Save intermediate results to `.tmp/enrichment_progress.json` to allow resuming.

## Error Handling
- **Search Failures**: If search fails or yields no results, mark as "Skipped".
- **Scrape Failures**: If site differs (403/404), Log error and proceed.
- **Rate Limits**: Add a small random delay (1-3s) between requests.
