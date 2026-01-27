# Email Discovery Techniques - Lessons Learned

## What Worked ✅

### 1. Direct Website Scraping (22.2% Success)
**Method**: Visit homepage + /contact page, extract emails via regex
**Why it worked**:
- Businesses put emails directly on their websites
- No complex search queries needed
- Works even for smaller businesses
- Bypasses privacy/blocking issues

**Implementation**:
```python
def scrape_website_simple(url):
    emails = set()
    # Homepage
    response = requests.get(url, timeout=10)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails.update(re.findall(email_pattern, response.text))
    
    # /contact page
    contact_url = urljoin(url, '/contact')
    response = requests.get(contact_url, timeout=10)
    emails.update(re.findall(email_pattern, response.text))
    return emails
```

### 2. Canonical URL Filter (20.4% Impact)
**Method**: Remove content pages (blog/, about/, service-area/)
**Why critical**:
- Content pages inflate dataset without providing leads
- Businesses have multiple URLs but only homepage matters
- Improves overall data quality

**Patterns to reject**:
```
/blog/, /about/, /service-area/, /news/, /article/
/residential-services/, /commercial-services/, /team/
News domains: dispatch.com, etc.
```

### 3. Email Tiering System
**Method**: Categorize by decision-making power
- Tier 1 (Owner): Named emails (maureen@, brian@, gary@)
- Tier 2 (Generic): info@, office@, hello@
- Tier 3 (Operational): support@, service@, customerservice@

**Impact**: Prioritizes outreach to decision makers

## What Didn't Work ❌

### 1. Owner Hunt via LinkedIn (0% Success)
**Why it failed**:
- Small HVAC businesses don't have strong LinkedIn presence
- Search queries too generic
- LinkedIn anti-scraping measures
- Requires paid LinkedIn Sales Navigator for accuracy

### 2. Social Rescue via Facebook (0% Success)
**Why it failed**:
- Business Facebook pages don't show emails publicly
- Need to be page admin to see contact info
- Facebook Graph API requires extensive permissions

## Advanced Techniques to Try Next

### 1. WHOIS Domain Lookup
- Query domain registration for owner email
- Works for smaller businesses who self-register

### 2. DNS MX Record Analysis
- Find mail server, guess common patterns
- firstname@domain, info@domain, contact@domain

### 3. Company Name + Email Search
- Google: "company name" email OR "company name" contact
- Bing advanced search with email TLD filter

### 4. Local Business Directory Scraping
- Better Business Bureau (BBB)
- Chamber of Commerce listings
- Industry-specific directories

### 5. Pattern Generation + Validation
- Extract owner name from "About" page
- Generate: firstname@domain, firstnamelastname@domain
- Validate using email verification API

## Storage Location
`c:\Users\Piyush\Downloads\lead enreaching agent\knowledge\`
- `email_discovery_techniques.md` (this file)
- `successful_patterns.json` (email patterns that worked)
- `failed_approaches.json` (what to avoid)
