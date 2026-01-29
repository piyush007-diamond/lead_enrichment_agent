# How to Add Your Tools to Vapi (Step-by-Step)

Follow these steps to give "Anjali" her brain. Use the details from **[vapi_tools_config.json](file:///c:/Users/Piyush/Downloads/voice%20agent/vapi_tools_config.json)**.

### 1. Go to Vapi Dashboard
- Navigate to **Assistants** -> select **Anjali**.
- Click on the **Tools** tab (or "Functions").

### 2. Create the "checkAvailability" Tool
Click **"Create New Tool"** or **"Add Tool"** and fill in as follows:

| Field | What to Paste | Purpose |
|-------|---------------|---------|
| **Name** | `checkAvailability` | This is what Anjali calls when she wants to check the calendar. |
| **Description** | `Check for available appointment slots for a specific date.` | Helps Anjali understand *when* to use this tool. |
| **Server URL** | `https://xf9j8k6oxqka.share.zrok.io/tools/checkAvailability` | **CRITICAL**: This is the tunnel to your local Python server. |
| **Parameters** | (Copy the `parameters` block from the JSON) | Defines the "Date" field that Anjali needs to tell the server. |

### 3. Create the "savePatient" Tool
Click **"Add Tool"** again:

| Field | What to Paste | Purpose |
|-------|---------------|---------|
| **Name** | `savePatient` | Anjali calls this when the user chooses a time. |
| **Description** | `Save or update patient details in the database.` | Tells Anjali to use this once she has name and phone. |
| **Server URL** | `https://xf9j8k6oxqka.share.zrok.io/tools/savePatient` | Sends the patient data to your Supabase database. |
| **Parameters** | (Copy the `parameters` block from the JSON) | Defines "name", "phone_number", etc. |

---

## 💡 Quick Tips
- **Method**: Set to `POST` (usually default).
- **Async Tool**: In Vapi, you can set "Tool is async" to true if you want Anjali to keep talking while waiting, but since our server is fast (<1s), you can leave it default.
- **Testing**: Once added, Anjali will see these tools. Try saying *"What's your availability for Friday?"* and watch your terminal logs! 🚀

![Your Tunnel is Active](file:///C:/Users/Piyush/.gemini/antigravity/brain/680d8bf6-e6e9-4019-aa5a-be5dd1b3b5ab/uploaded_media_1769554521885.png)
*(Your server is ready at the URL above!)*
