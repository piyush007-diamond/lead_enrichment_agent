# 🔐 Multi-Client Authentication & Customization Guide

> **Clarifying**: How client-specific prompts, emails, and Google OAuth work in production

---

## 1️⃣ Assistant Prompt Customization (Per-Business)

### The Question
> "Assistant prompt will be different for each business"

### ✅ Yes, Absolutely! Each Client Gets Custom Prompt

**How It Works:**

```sql
-- In your clients table (Supabase)
CREATE TABLE clients (
    id UUID PRIMARY KEY,
    business_name TEXT,              -- e.g., "Balaji ENT Hospital"
    business_type TEXT,              -- e.g., "hospital", "salon", "gym"
    custom_greeting TEXT,            -- "Namaste. This is Anjali from Balaji..."
    operating_hours JSONB,           -- {"Mon": "9-5", "Tue": "9-5"}
    assistant_personality TEXT,      -- "professional", "friendly", "casual"
    vapi_assistant_id TEXT,
    gcal_refresh_token TEXT,
    business_email TEXT,             -- Their Gmail for confirmations
    -- ... other fields
);
```

**Dynamic Prompt Generation:**

```python
# In your server.py (when Vapi calls your webhook)
@app.post("/client/{client_id}/tool")
async def handle_tool_call(client_id: str, request: Request):
    # 1. Load client config from database
    client = await supabase.table('clients').select('*').eq('id', client_id).single()
    
    # 2. Use client-specific data for responses
    business_name = client['business_name']  # "Balaji ENT Hospital"
    greeting = client['custom_greeting']     # "Namaste. This is Anjali..."
    
    # 3. Generate response with their branding
    return {
        "result": f"{greeting} from {business_name}. How can I help you today?"
    }
```

**BUT WAIT - Vapi Prompt is Set Once Per Assistant!**

You have **two options**:

### Option A: Create New Assistant Per Client (Recommended)
```python
# When client signs up:
vapi_response = requests.post(
    "https://api.vapi.ai/assistant",
    headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
    json={
        "name": f"Assistant for {client['business_name']}",
        "model": {
            "provider": "openai",
            "model": "gpt-4",
            "systemPrompt": f"""
You are a receptionist for {client['business_name']}, 
a {client['business_type']}.

Greeting: {client['custom_greeting']}
Operating Hours: {client['operating_hours']}
Personality: {client['assistant_personality']}

Follow the booking flow...
"""
        },
        "serverUrl": f"https://your-server.railway.app/client/{client.id}",
        # ... rest of assistant config
    }
)
```

**Result:** Each client gets their own Vapi assistant with their own prompt!

### Option B: Single Assistant, Dynamic Prompt Injection
```python
# Use Vapi's "knowledgeBase" or "variables" feature (if available)
# OR inject context in first tool response
return {
    "result": f"[CONTEXT: Business={business_name}, Hours={hours}] {actual_response}"
}
```

**Recommended:** **Option A** (separate assistants) for clean separation.

---

## 2️⃣ Client Email for Confirmations

### The Question
> "Their email will be needed to send confirmations"

### ✅ Two Types of Emails

**Type 1: Business Email (Sender)**
- **Question**: Who sends the confirmation email?
- **Answer**: Either YOU (via your SendGrid) OR the client (via their Gmail)

**Option A: Your Centralized Email (Easier)**
```python
# You use SendGrid (or similar)
# Emails appear to come from: noreply@yourvoiceagent.com
# But signature says: "Balaji ENT Hospital"

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email='noreply@yourvoiceagent.com',
    to_emails=patient_email,
    subject=f'Appointment Confirmation - {client["business_name"]}',
    html_content=f"""
    <h2>{client["business_name"]}</h2>
    <p>Your appointment is confirmed...</p>
    """
)

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
response = sg.send(message)
```

**Pros:** 
- ✅ No Gmail password needed from client
- ✅ Better deliverability
- ✅ Easier to manage

**Cons:**
- ⚠️ Emails come from your domain (not theirs)

**Option B: Client's Gmail (More Authentic)**
```python
# Store client's Gmail credentials (encrypted)
# Use their SMTP to send

import smtplib

gmail_user = decrypt(client['gmail_address'])
gmail_password = decrypt(client['gmail_app_password'])

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(gmail_user, gmail_password)
    smtp.send_message(...)
```

**Pros:**
- ✅ Emails come from client's actual email
- ✅ More trustworthy for patients

**Cons:**
- ⚠️ Need to collect Gmail App Password from client
- ⚠️ Security risk (storing passwords)

**Type 2: Patient Email (Recipient)**
- This is collected during the call (Vapi asks patient)
- Stored in `patients` table: `email` column
- Used to send confirmation to patient

---

## 3️⃣ Vapi Agent Creation (Behind the Scenes)

### The Question
> "Vapi agent created from my account, client will never know what's going on backside"

### ✅ Correct! White-Label Service

**How Client Sees It:**
```
1. Client goes to: yourvoiceagent.com/signup
2. Enters business name, connects Google Calendar
3. Gets phone number: +1 (555) 123-4567
4. They call it → Hears their custom greeting
5. They think: "This is my AI receptionist!"
```

**What's Actually Happening (Hidden from Client):**
```
1. Your system creates Vapi assistant under YOUR account
2. Charges go to YOUR credit card
3. Client never sees Vapi.ai
4. Client never knows you're using Supabase
5. You mark up costs and charge client
```

**Analogy:** Like a restaurant:
- Customer orders "Chicken Curry"
- They don't know you bought chicken from Walmart
- They don't know you used XYZ spices brand
- They just enjoy the meal and pay YOU

**Your Pricing Example:**
- Vapi charges YOU: $0.05/minute
- You charge CLIENT: $0.12/minute
- Your profit: $0.07/minute

**Important:** You OWN the relationship. Client pays you, not Vapi.

---

## 4️⃣ Google OAuth & "Testing Users" Confusion

### The Question
> "By creating authentication, they will be stored as testing users in my app in Google Cloud Console?"

### ❌ No! This is a Common Misconception

Let me clarify the **two different Google OAuth scenarios**:

### Scenario A: During Development (What You've Been Doing)
```
Google Cloud Console → OAuth Consent Screen
Status: "Testing"
Allowed Users: 
  - piyushhire091@gmail.com  ← Your email
  - test@example.com         ← You manually add
```

**Effect:** Only these specific emails can authorize your app to access their calendar.

**Problem:** You can't scale to 100 clients this way (manual adding is tedious).

---

### Scenario B: Production (What You Need)

**Step 1: Verify Your Domain**
```
Google Cloud Console → OAuth Consent Screen
1. Add your domain: yourvoiceagent.com
2. Verify via DNS/HTML file upload
```

**Step 2: Submit for Verification**
```
Publishing Status: "In Production"
Verification: Submit app for Google review
    - Privacy Policy URL
    - Terms of Service URL
    - App homepage
    - Why you need calendar access (explain use case)
```

**Review Time:** 3-7 days typically

**After Approval:**
```
✅ ANY Gmail user can authorize your app
✅ No "testing users" list needed
✅ Consent screen shows your verified domain
✅ Professional appearance
```

**What Client Sees During OAuth:**
```
┌─────────────────────────────────────────┐
│  Sign in with Google                    │
├─────────────────────────────────────────┤
│  [Your Voice Agent Logo]                │
│                                         │
│  yourvoiceagent.com wants to:          │
│   ☑ View and manage your calendar      │
│                                         │
│  ✓ Verified by Google                  │
│                                         │
│  [Cancel]  [Allow]                      │
└─────────────────────────────────────────┘
```

**Important Notes:**

1. **Clients are NOT "testing users"** - They are authorizing YOUR app to access THEIR calendar
2. **Each client authorizes independently** - Your system stores their `refresh_token`
3. **No manual addition needed** - Once verified, anyone can use it
4. **Client owns their data** - They can revoke access anytime

---

## 5️⃣ Complete Onboarding Flow (Real Example)

### Client Perspective:
```
1. Visit: yourvoiceagent.com
2. Click "Start Free Trial"
3. Fill form:
   - Business Name: "Dr. Smith Dental Clinic"
   - Business Type: "Dental"
   - Email: dr.smith@example.com
   - Phone: +1-555-0100

4. Click "Connect Google Calendar"
   → Redirected to Google OAuth
   → Signs in with their work Gmail
   → Clicks "Allow"
   → Redirected back to your site

5. System shows:
   ┌─────────────────────────────────┐
   │ ✓ Setup Complete!               │
   │                                 │
   │ Your AI Phone Number:           │
   │ +1 (555) 987-6543              │
   │                                 │
   │ [Test Call] [Go to Dashboard]   │
   └─────────────────────────────────┘

6. They call the number → Hear their custom greeting
7. Done!
```

### Backend (What Your System Does Automatically):
```python
@app.post("/api/onboard")
async def onboard_client(data: dict):
    # 1. Create client record
    client = await supabase.table('clients').insert({
        'business_name': data['business_name'],
        'business_email': data['email'],
        'custom_greeting': f"Hello, welcome to {data['business_name']}",
        # ... other fields
    }).execute()
    
    # 2. Redirect to Google OAuth
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri=https://yourvoiceagent.com/oauth/callback&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/calendar&"
        f"state={client.id}"  # To link back to client
    )
    return {"redirect": oauth_url}

@app.get("/oauth/callback")
async def oauth_callback(code: str, state: str):
    client_id = state  # Retrieve client ID
    
    # 3. Exchange code for refresh_token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": "https://yourvoiceagent.com/oauth/callback",
            "grant_type": "authorization_code"
        }
    )
    
    refresh_token = token_response.json()['refresh_token']
    
    # 4. Store encrypted token
    await supabase.table('clients').update({
        'gcal_refresh_token': encrypt(refresh_token)
    }).eq('id', client_id).execute()
    
    # 5. Create Vapi assistant
    client = await get_client(client_id)
    vapi_response = create_vapi_assistant(client)
    
    # 6. Save assistant ID and phone number
    await supabase.table('clients').update({
        'vapi_assistant_id': vapi_response['id'],
        'phone_number': vapi_response['phoneNumber']
    }).eq('id', client_id).execute()
    
    # 7. Redirect to success page
    return RedirectResponse("/onboarding-complete")
```

---

## 6️⃣ What Client Needs to Provide (Minimal)

### Required:
1. ✅ **Business Name** (text input)
2. ✅ **Google Calendar Access** (OAuth button - 2 clicks)
3. ✅ **Email Address** (for login + optional confirmation sender)
4. ✅ **Operating Hours** (simple dropdown/form)

### Optional (You Can Set Defaults):
5. ⚪ Assistant personality (default: "professional")
6. ⚪ Greeting message (default: auto-generated from business name)
7. ⚪ Appointment duration (default: 60 minutes)

### NOT Required:
- ❌ Vapi API key
- ❌ Supabase credentials
- ❌ Technical knowledge
- ❌ Server setup
- ❌ Domain configuration

---

## 7️⃣ Storing Client Data (Security Best Practices)

```sql
-- clients table structure
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Business Info (Public)
    business_name TEXT NOT NULL,
    business_type TEXT,
    business_email TEXT NOT NULL,
    phone_number TEXT,  -- Their voice agent number
    
    -- Customization (Public)
    custom_greeting TEXT,
    operating_hours JSONB,
    assistant_personality TEXT DEFAULT 'professional',
    
    -- Integration IDs (Private - not shown to client)
    vapi_assistant_id TEXT UNIQUE,
    
    -- Sensitive Credentials (ENCRYPTED)
    gcal_refresh_token TEXT,  -- encrypt(token)
    gmail_app_password TEXT,  -- encrypt(password) - if using their SMTP
    
    -- Billing
    subscription_plan TEXT DEFAULT 'free_trial',
    monthly_limit_minutes INT DEFAULT 500,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Encryption Example:**
```python
from cryptography.fernet import Fernet
import os

# Generate once, store in Railway env vars
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

def encrypt(value: str) -> str:
    return cipher.encrypt(value.encode()).decode()

def decrypt(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()
```

---

## 📋 Summary

| Aspect | How It Works |
|--------|-------------|
| **Custom Prompts** | Each client gets their own Vapi assistant with unique system prompt |
| **Email Sender** | Option A: Your SendGrid (easier). Option B: Their Gmail (more authentic) |
| **Vapi Account** | YOU own the account, client never knows. White-label service. |
| **Google OAuth** | Client authorizes YOUR app (once verified). NOT "testing users". |
| **Client Setup** | 5 minutes: Name + Google OAuth button. Done. |
| **Your Profit** | Vapi charges $0.05/min → You charge client $0.12/min |

**Client Experience:** "I have my own AI receptionist with my own phone number!"  
**Reality:** You're reselling Vapi + Google Calendar + Supabase as a packaged service.

---

*No code changes made - pure clarification as requested!*
