# 🚀 Multi-Client Deployment Strategy Research

> **Goal**: Transition from single-client local setup to production-ready SaaS platform

---

## 📋 Current State Analysis

### What You Have Now (Single Client, Local)
```
┌─────────────────────────────────────────┐
│  Your Local Machine                     │
│  ┌─────────────────────────────────┐   │
│  │ start_agent.bat                 │   │
│  │  ├─ Runs server.py (FastAPI)    │   │
│  │  ├─ Runs zrok tunnel            │   │
│  │  └─ Updates Vapi tools          │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Environment Variables (.env):         │
│  - GOOGLE_CREDENTIALS                  │
│  - SUPABASE_URL (your project)         │
│  - GMAIL_PASSWORD                      │
│  - VAPI_API_KEY                        │
└─────────────────────────────────────────┘
         ↓ (must restart manually)
```

### Problems with Current Approach for Multiple Clients
1. ❌ **No isolation**: All clients would share same Supabase tables
2. ❌ **Manual setup**: Each client needs you to create new config files
3. ❌ **Not scalable**: Can't run 10 clients on your laptop
4. ❌ **Downtime risk**: If your PC shuts down, all clients go offline
5. ❌ **Security risk**: Client credentials stored in plaintext on your machine

---

## 🏗️ Industry Standard Architectures

### Option 1: Multi-Tenant SaaS (Shared Infrastructure)
**How companies like Calendly, Intercom, Zendesk do it**

```
┌──────────────────────────────────────────────────────┐
│  Cloud Server (e.g., Railway, Render, AWS)           │
│  ┌────────────────────────────────────────────────┐ │
│  │ Your FastAPI Server (Always Running)           │ │
│  │                                                 │ │
│  │  /client/ABC/checkAvailability  ──▶ Logic      │ │
│  │  /client/XYZ/checkAvailability  ──▶ Logic      │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Single Supabase Instance (Your Account)            │
│  ┌────────────────────────────────────────────────┐ │
│  │ Table: clients (id, name, vapi_key, etc.)      │ │
│  │ Table: patients (id, client_id, name, phone)   │ │
│  │ Table: calendars (id, client_id, gcal_creds)   │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
               ↓
    Each Client has their own:
    - Vapi Assistant (different phone number)
    - Google Calendar (their credentials stored encrypted)
    - Row Isolation (WHERE client_id = 'ABC')
```

**Pros:**
- ✅ One codebase, one server
- ✅ Easy to maintain and update
- ✅ Cost-effective (shared resources)
- ✅ Simple to add new clients (just insert row in DB)

**Cons:**
- ⚠️ Requires secure credential storage (encryption)
- ⚠️ Data isolation logic must be perfect (security risk if leaked)
- ⚠️ Single point of failure (if server down, all clients affected)

---

### Option 2: Isolated Instances (Per-Client Deployment)
**How companies like Retool, n8n (self-hosted) do it**

```
Client A:
┌────────────────────────────────┐
│ Railway App Instance #1        │
│ - server.py (only for A)       │
│ - A's Supabase credentials     │
│ - A's Google Calendar          │
│ Public URL: a-agent.railway.app│
└────────────────────────────────┘

Client B:
┌────────────────────────────────┐
│ Railway App Instance #2        │
│ - server.py (only for B)       │
│ - B's Supabase credentials     │
│ - B's Google Calendar          │
│ Public URL: b-agent.railway.app│
└────────────────────────────────┘
```

**Pros:**
- ✅ Complete isolation (very secure)
- ✅ Client can self-host if they want
- ✅ No risk of data leakage between clients
- ✅ Client-specific customizations easier

**Cons:**
- ❌ Expensive (need to pay for each instance)
- ❌ Hard to maintain (updates must be deployed 10 times)
- ❌ Redundant resources (10 clients = 10 servers)

---

### Option 3: Hybrid (Recommended for Your Case)
**Combine benefits of both**

```
┌──────────────────────────────────────────────────────┐
│  Your Central Server (Railway/Render - Always On)    │
│  ┌────────────────────────────────────────────────┐ │
│  │ Multi-Tenant FastAPI Server                    │ │
│  │                                                 │ │
│  │ Route by Vapi Assistant ID:                    │ │
│  │  - Request → Extract client_id from webhook    │ │
│  │  - Load client config from DB                  │ │
│  │  - Execute with client's credentials           │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Your Supabase (Single Instance, Multi-Tenant)      │
│  ┌────────────────────────────────────────────────┐ │
│  │ clients (id, name, gcal_oauth_token, etc.)     │ │
│  │ patients (id, client_id, name, phone, date)    │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
               ↓
    Each Client uses:
    - Their own Vapi Assistant (you create via API)
    - Their own Google Calendar (OAuth flow to get token)
    - Isolated rows in shared Supabase tables
```

**Why This Is Best for You:**
1. ✅ One server to deploy and maintain
2. ✅ Easy onboarding (just OAuth + webhook setup)
3. ✅ Scales to 100+ clients on same server
4. ✅ Cost-effective ($10-20/month for all clients vs $10/client)

---

## 🎯 Recommended Implementation Path

### Phase 1: Move to Cloud (Remove Bat File Dependency)

**Deploy to Railway/Render:**
```bash
# Instead of start_agent.bat, deploy once:
git push railway main

# Server runs 24/7 at:
https://your-voice-agent.railway.app
```

**Environment Variables (Set Once in Railway Dashboard):**
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `VAPI_API_KEY` (your master key)
- *(Client-specific creds will be in DB, not env vars)*

**Public URL is Permanent** (no more zrok dynamic URLs)

---

### Phase 2: Multi-Tenant Database Schema

**Add to Supabase:**
```sql
-- New table: clients
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    vapi_assistant_id TEXT UNIQUE,
    gcal_refresh_token TEXT,  -- Encrypted
    gmail_password TEXT,      -- Encrypted (or skip, use SendGrid)
    webhook_secret TEXT,      -- For security
    created_at TIMESTAMP DEFAULT NOW()
);

-- Modify existing table: patients
ALTER TABLE patients 
ADD COLUMN client_id UUID REFERENCES clients(id);

-- Add Row Level Security (RLS)
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON patients
    USING (client_id = current_setting('app.current_client_id')::UUID);
```

**Now each client's data is isolated automatically.**

---

### Phase 3: Client Onboarding Dashboard

**What You Build (Simple Web App):**
```
Landing Page (https://your-voice-agent.com)
    ↓
Client Signup Form:
    - Name
    - Email
    - Phone Number
    ↓
Onboarding Steps:
    1. Connect Google Calendar (OAuth button)
       → Saves refresh_token to clients table
    2. Connect Vapi Phone Number (your script creates assistant via API)
    3. Test Call (dial number to verify)
    ↓
Client Dashboard:
    - View appointments
    - Analytics
    - Settings
```

**Backend Automation (What You Code):**
```python
@app.post("/api/onboard-client")
async def onboard_client(data: dict):
    # 1. Create client row in Supabase
    client = await supabase.table('clients').insert({
        'name': data['name'],
        'email': data['email']
    }).execute()
    
    # 2. Create Vapi Assistant via API
    vapi_response = requests.post(
        "https://api.vapi.ai/assistant",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
        json={
            "name": f"Assistant for {data['name']}",
            "serverUrl": f"https://your-voice-agent.railway.app/client/{client.id}",
            "model": {...}
        }
    )
    
    # 3. Save assistant ID
    await supabase.table('clients').update({
        'vapi_assistant_id': vapi_response.json()['id']
    }).eq('id', client.id).execute()
    
    # 4. Return success + phone number to client
    return {"phone": vapi_response.json()['phoneNumber']}
```

**Client Onboarding Flow (What Client Sees):**
1. They go to your website
2. Click "Sign Up"
3. Click "Connect Google Calendar" → Standard OAuth (like "Sign in with Google")
4. Your system auto-creates their Vapi assistant
5. They get their phone number instantly
6. Done! (No manual setup)

---

## 🔑 What to Collect from Each Client

### Required Information:
1. **Google Calendar Access** (via OAuth - they just click "Allow")
2. **Email** (for notifications - or use your SendGrid account)
3. **Business Name** (for branding)
4. **Operating Hours** (for slot calculation)

### What You DON'T Need from Them:
- ❌ Supabase credentials (they use YOUR instance)
- ❌ Vapi key (you create assistants under YOUR account)
- ❌ Technical setup (all automated)

---

## 💰 Pricing Models (How to Charge)

### Option A: Per-Minute Calling
- $0.05/min (what Vapi charges you)
- You charge client $0.10/min (50% markup)
- Monthly bill = Minutes used × $0.10

### Option B: Monthly Subscription
- Starter: $49/month (500 minutes included)
- Pro: $149/month (2000 minutes included)
- Overage: $0.08/min

### Option C: Per-Appointment
- $2 per booked appointment
- Simple, predictable for small clinics

---

## 🔒 Security Considerations

### Credential Storage (Critical)
```python
# DON'T store plaintext:
# client.gcal_token = "ya29.a0AfH6..."  ❌

# DO encrypt before saving:
from cryptography.fernet import Fernet

def encrypt_token(token: str) -> str:
    key = os.getenv("ENCRYPTION_KEY")  # Store in Railway env vars
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    key = os.getenv("ENCRYPTION_KEY")
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

### Webhook Verification
```python
# Verify requests are really from Vapi (prevent spoofing)
@app.post("/client/{client_id}/checkAvailability")
async def check_availability(client_id: str, request: Request):
    # Verify HMAC signature
    signature = request.headers.get("X-Vapi-Signature")
    if not verify_signature(signature, await request.body()):
        raise HTTPException(403, "Invalid signature")
    
    # Load client config
    client = await get_client(client_id)
    # ... rest of logic
```

---

## 📊 Comparison Table

| Aspect | Current (Local) | Multi-Tenant SaaS | Isolated Instances |
|--------|----------------|-------------------|-------------------|
| **Cost** | $0 | $20/month total | $10/month per client |
| **Scalability** | 1 client | 100+ clients | Limited by budget |
| **Maintenance** | Manual | Single update | Update each instance |
| **Uptime** | 0% (when PC off) | 99.9% | 99.9% per instance |
| **Onboarding Time** | 2 hours manual | 5 minutes automated | 30 minutes automated |
| **Best For** | Testing | SaaS product | Enterprise/Self-hosted |

---

## 🎬 Step-by-Step Migration Plan

### Week 1: Cloud Deployment (No Multi-Tenancy Yet)
1. ✅ Deploy current code to Railway/Render
2. ✅ Replace zrok with permanent URL
3. ✅ Test with your single client (yourself)
4. ✅ Verify 24/7 uptime

### Week 2: Database Multi-Tenancy
1. ✅ Add `clients` table to Supabase
2. ✅ Add `client_id` column to `patients`
3. ✅ Modify server.py to load client config from DB
4. ✅ Test with 2 test clients (yourself + dummy)

### Week 3: Onboarding Automation
1. ✅ Build simple signup form (HTML page)
2. ✅ Implement Google OAuth flow
3. ✅ Auto-create Vapi assistants via API
4. ✅ Test end-to-end onboarding

### Week 4: Client Dashboard
1. ✅ Show client's appointments
2. ✅ Analytics (calls, bookings, revenue)
3. ✅ Settings (operating hours, etc.)

---

## 🤔 My Recommendation

**Start with Multi-Tenant SaaS (Option 3 - Hybrid):**

1. **Deploy to Railway** ($5-10/month, permanent URL)
2. **Add `clients` table** to your existing Supabase
3. **Build simple onboarding** (Google OAuth + auto Vapi setup)
4. **Charge per appointment** ($2 per booking, easy to explain)

**Why?**
- You can onboard new clients in 5 minutes (vs 2 hours now)
- One codebase = easy updates
- Scales to 50+ clients without changing architecture
- Total cost: $10-20/month (covers all clients)

---

*Next Steps: Review this research, then I can help you implement Phase 1 (Cloud Deployment)*
