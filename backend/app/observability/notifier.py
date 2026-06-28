import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from app.config import settings

class EmailNotifier:
    """Sends email notifications for system events (e.g. human-in-the-loop approvals)."""
    
    def send_notification(self, subject: str, html_content: str):
        """Sends an email notification. Fired synchronously/asynchronously."""
        provider = (settings.EMAIL_PROVIDER or "mock").lower()
        
        if provider == "mock":
            print(f"\n--- [EmailNotifier MOCK OUTPUT] ---")
            print(f"Subject: {subject}")
            print(f"To: {settings.NOTIFY_EMAIL or 'unconfigured'}")
            print(f"Body Preview:\n{html_content[:300]}...")
            print(f"-----------------------------------\n")
            return
            
        if provider == "resend":
            if not settings.RESEND_API_KEY:
                print("[EmailNotifier WARNING] Resend API key is missing. Skipped.")
                return
            try:
                import httpx
                url = "https://api.resend.com/emails"
                headers = {
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "from": "NexusAI <onboarding@resend.dev>",
                    "to": [settings.NOTIFY_EMAIL or "admin@nexusai.dev"],
                    "subject": subject,
                    "html": html_content
                }
                # Sync post call for simplicity inside standard run loops
                response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code in [200, 201]:
                    print(f"[EmailNotifier] Resend email sent successfully for: {subject}")
                else:
                    print(f"[EmailNotifier ERROR] Resend failed with code {response.status_code}: {response.text}")
            except Exception as e:
                print(f"[EmailNotifier ERROR] Resend API call failed: {e}")
                
        else:  # Default: SMTP (Option 1: Gmail App Passwords / generic SMTP)
            if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
                print("[EmailNotifier WARNING] SMTP credentials are not configured in settings. Email skipped.")
                return
                
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"NexusAI <{settings.SMTP_USER}>"
                msg["To"] = settings.NOTIFY_EMAIL or settings.SMTP_USER
                
                part = MIMEText(html_content, "html", "utf-8")
                msg.attach(part)
                
                # Connect to SMTP server using TLS
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                    
                print(f"[EmailNotifier] SMTP notification email sent to {msg['To']} for: {subject}")
            except Exception as e:
                print(f"[EmailNotifier ERROR] SMTP email send failed: {e}")

# Shared notifier instance
notifier = EmailNotifier()
