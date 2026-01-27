# Directive: Validate Dentist Data

## Objective
Provide "100% Surety" (or as close as possible) for the credibility of the enriched dentist leads by cross-referencing with official government data and verifying digital footprints.

## Inputs
- **Input File**: `dentist.leads.arizona.enriched.csv`

## Validation Steps

### 1. Doctor Verification (NPI Registry)
- **Source**: CMS National Plan and Provider Enumeration System (NPPES) API.
- **Action**: Query the registry using the extracted `Doctor Name` and `State=AZ`.
- **Criteria**:
    - Must match First Name and Last Name.
    - Taxonomy should relate to "Dentist", "General Practice", "Orthodontics", etc.
- **Output**: `NPI_Number`, `NPI_Status` (Active/Inactive), `NPI_Verified` (Boolean).

### 2. Email Verification
- **Domain Match**: Check if the email domain matches the business website domain (e.g., `info@smileaz.com` matches `www.smileaz.com`).
- **Generic Check**: Flag emails using `gmail.com`, `yahoo.com`, `outlook.com` as "Personal/Generic".
- **Syntax Check**: Ensure valid email format.
- **Output**: `Email_Match_Type` (Domain Match, Generic, Mismatch), `Email_Verified` (Boolean).

### 3. Confidence Scoring
- **High Quality**: `NPI_Verified` is True AND (`Email_Match_Type` is 'Domain Match' OR 'Personal').
- **Medium Quality**: `NPI_Verified` is True OR `Email_Match_Type` is 'Domain Match'.
- **Low Quality**: Neither.

## Outputs
- **Final File**: `dentist.leads.arizona.verified.csv`
- **Report**: Summary of how many leads passed the high-confidence threshold.
