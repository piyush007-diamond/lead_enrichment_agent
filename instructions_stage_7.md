# Stage 7: End-to-End Testing (User Instructions)

## Status: 🚀 READY FOR LAUNCH

We have built and verified the "Brain" of the agent. Now we need to connect it to Vapi.

### Step 1: Start the Server
1. **Open a Terminal** (VS Code Terminal).
2. **Start the Brain**:
   ```powershell
   python -m execution.server
   ```
   *(Ensure you see "Application startup complete" and "Google Calendar Service Initialized")*

### Step 2: Start Tunnel (Choose ngrok OR zrok)

#### Option A: Using ngrok (Easier, but URL changes)
1. **Open a SECOND Terminal**.
2. Run: `ngrok http 8000`
3. Copy the `https` URL (e.g., `https://xxxx.ngrok-free.app`).

#### Option B: Using zrok (Recommended for Stable URLs)
You asked about keeping the URL same using `zrok`. Here is how:

**To create a PERMANENT URL (Reserved):**
1. **Open a SECOND Terminal**.
2. Reserve a public backend:
   ```powershell
   
   
   ```
3. It will print a **Token** (e.g., `uv4...`). Copy this token.
4. Start the share using the token:
   ```powershell
   zrok share public <YOUR_TOKEN>
   ```
5. Copy the **Access Point** URL (e.g., `https://uv4....share.zrok.io`).
   - This URL will REMAIN THE SAME as long as you use that token!

**To create a TEMPORARY URL (Quick):**
1. Run: `zrok share public localhost:8000`

### Step 3: Configure Vapi Tools
1. Open your **Vapi Dashboard** -> **Assistants** -> **Anjali**.
2. Go to the **Tools** section.
3. **Open `vapi_tools_config.json`** file I created in your workspace.
4. **Replace `<YOUR_NGROK_URL>`** in that file with your actual tunnel URL (zrok or ngrok).
   - Example: `https://my-stable-url.share.zrok.io/tools/checkAvailability`
5. Add/Update the tools in Vapi with this configuration:
   - Tool 1: `checkAvailability`
   - Tool 2: `savePatient`

### Step 4: Test the Call
1. Interact with the agent on Vapi (web call or phone).
2. **Scenario**:
   - "Hi Anjali, I want to book an appointment."
   - "Can I come in tomorrow?"
   - (Agent should check calendar via your server and respond)
   - "Great, book me for 10am."
   - "My name is [Name]..."
   - (Agent should confirm and save to database)

### Troubleshooting
- **If Agent says "System error"**: Check your Python terminal logs.
- **If Agent ignores tools**: Check Vapi "Logs" -> "Tool Calls" to see if it hit your server.
