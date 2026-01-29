# System Lifecycle & Deployment

## System Context (Brain)
This skill governs the "Body" of the Voice Agent. It ensures the backend server is running, accessible from the internet, and synchronized with the Vapi Cloud "Brain".
Without this, the AI (Anjali) exists in the cloud but has no hands or eyes (tools) to act on the hospital's data.

### Rules
1.  **Always Start Clean**: The launcher kills old processes (uvicorn, zrok) to prevent port conflicts.
2.  **Dynamic Tunneling**: We use Zrok (headless) to get a public URL (`https://...share.zrok.io`). This URL changes every session, so we MUST update Vapi immediately (Auto-Sync).
3.  **One-Click Experience**: The user should only interact with `start_agent.bat`.

## Tools & Scripts
-   `start_agent.bat`: Windows batch file that sets environment and runs `launcher.py`.
-   `execution/launcher.py`: The master coordinator script.
    -   Starts `server.py` (FastAPI) on port 8000.
    -   Starts `zrok share` tunnel.
    -   Scrapes the public URL from Zrok output.
    -   Calls `vapi_update_tools.py` to update the cloud.

## Interconnections
-   **Dependencies**: Requires `server.py` (Voice Integration Skill) to be bug-free to start.
-   **Triggers**: Once the tunnel is up, it triggers `vapi_update_tools.sync_tools()` to update the `VOICE_INTEGRATION` layer.
-   **Affects**: The entire availability of the system. If this fails, the AI says "I'm having trouble connecting".

## Output Contract
-   **Success State**:
    -   Server running on localhost:8000 (PID active).
    -   Zrok tunnel active (Public URL reachable).
    -   Console prints: `✨ SYSTEM READY! You can now talk to the Voice Agent.`
-   **Physical Side Effects**:
    -   Creates/Overwrites `server_launcher.log`.
    -   Updates Vapi Tool Definitions with the NEW dynamic URL.
