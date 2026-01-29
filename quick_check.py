import requests
try:
    print("Health check:", requests.get("http://localhost:8000/", timeout=2).json())
except Exception as e:
    print("Failed:", e)
