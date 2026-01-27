import smtplib
import dns.resolver
import socket

def check_smtp_connectivity():
    domain = "gmail.com"
    try:
        # 1. MX Lookup
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        print(f"MX Record for {domain}: {mx_record}")
        
        # 2. Connect to Port 25
        print(f"Attempting to connect to {mx_record}:25...")
        server = smtplib.SMTP(mx_record, 25, timeout=5)
        server.ehlo()
        print("Success: Connected to Port 25!")
        server.quit()
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    check_smtp_connectivity()
