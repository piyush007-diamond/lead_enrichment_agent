import subprocess
import time
import re
import sys
import threading
import os

# Add project root to sys.path so we can import 'execution' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from execution.vapi_update_tools import sync_tools, NEW_URL_BASE, TOOLS_CONFIG
import execution.vapi_update_tools as vapi_tools_module

def read_stream(stream, callback):
    """
    Reads a stream line by line and invokes callback.
    """
    for line in iter(stream.readline, ''):
        callback(line)
    stream.close()

class Launcher:
    def __init__(self):
        self.server_process = None
        self.tunnel_process = None
        self.public_url = None
        self.stop_event = threading.Event()

    def start_server(self):
        print("🚀 Starting FastAPI Server on port 8000...")
        # Open log file
        self.log_file = open("server_launcher.log", "w")
        
        # Start uvicorn in a separate process
        self.server_process = subprocess.Popen(
            [sys.executable, "-u", "-m", "uvicorn", "execution.server:app", "--port", "8000"],
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        # We don't strictly need to monitor server output line-by-line for this simple launcher
        # but we could. For now, we trust it starts.
        time.sleep(2) # Give it a moment
        
        if self.server_process.poll() is not None:
            print("❌ Server failed to start! Check server_launcher.log for details.")
            # Print the log content to console for visibility
            self.log_file.close() # Close write handle
            with open("server_launcher.log", "r") as f:
                print(f.read())
            sys.exit(1)
            
        print("✅ Server process started (logs in server_launcher.log).")

    def start_tunnel_and_update(self):
        print("🚇 Starting Zrok Tunnel...")
        # Start zrok share
        self.tunnel_process = subprocess.Popen(
            ["zrok", "share", "public", "http://localhost:8000", "--headless"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Thread to read output and find URL
        def check_output(line):
            print(f"[zrok] {line.strip()}")
            if not self.public_url:
                # Regex to find https://<hash>.share.zrok.io
                match = re.search(r'(https://[a-zA-Z0-9]+\.share\.zrok\.io)', line)
                if match:
                    self.public_url = match.group(1)
                    print(f"\n🎉 FOUND TUNNEL URL: {self.public_url}\n")
                    self.update_vapi()

        t = threading.Thread(target=read_stream, args=(self.tunnel_process.stdout, check_output))
        t.daemon = True
        t.start()

    def update_vapi(self):
        print("🔄 Updating Vapi Configuration with new URL...")
        
        # Update the module-level variable
        vapi_tools_module.NEW_URL_BASE = self.public_url
        
        # Update the config dictionaries logic
        for tool in vapi_tools_module.TOOLS_CONFIG:
            if "server" in tool:
                # vapi_update_tools.py structure: "function": {"name": ...} or top level "name"
                # Check structure in vapi_update_tools.py
                # Step 2277 shows structure is:
                # { "name": "cancelAppointment", "function": {...}, "server": ... }
                # So tool["name"] is valid.
                
                tool_name = tool["name"]
                tool["server"]["url"] = f"{self.public_url}/tools/{tool_name}"
        
        # Now call the function
        try:
            vapi_tools_module.sync_tools()
            print("\n✨ SYSTEM READY! You can now talk to the Voice Agent.\n")
            print("Press Ctrl+C to stop.")
        except Exception as e:
            print(f"❌ Failed to update Vapi: {e}")

    def run(self):
        try:
            self.start_server()
            self.start_tunnel_and_update()
            
            # Keep main thread alive
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.cleanup()

    def cleanup(self):
        if self.tunnel_process:
            print("Killing tunnel...")
            self.tunnel_process.terminate()
        if self.server_process:
            print("Killing server...")
            self.server_process.terminate()

if __name__ == "__main__":
    launcher = Launcher()
    launcher.run()
