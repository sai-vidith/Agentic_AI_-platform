import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from app.config import settings

class EmailNotifier:
    """Sends email notifications for system events (e.g. human-in-the-loop approvals)."""
    
    def _remove_emojis(self, text: str) -> str:
        if not text:
            return ""
        import re
        # Match emojis and miscellaneous/pictorial characters to clean subject/body text
        emoji_pattern = re.compile(
            "["
            "\U00010000-\U0010ffff"
            "\u2600-\u27bf"
            "\u2300-\u23ff"
            "\u2b50"
            "\u2934-\u2935"
            "\u2b05-\u2b07"
            "]+", 
            flags=re.UNICODE
        )
        return emoji_pattern.sub("", text)
        
    def send_notification(self, subject: str, html_content: str):
        """Standard entrypoint. Queues notification if digest mode is enabled, else sends immediately."""
        clean_subject = self._remove_emojis(subject)
        clean_html = self._remove_emojis(html_content)
        
        if settings.EMAIL_DIGEST_MODE:
            from app.core.event_store import event_store
            event_store.queue_notification(clean_subject, clean_html)
            print(f"[EmailNotifier] Queued notification for digest: {clean_subject}")
        else:
            self.send_notification_raw(clean_subject, clean_html)

    def send_digest(self):
        """Gathers all queued notifications, aggregates them, and sends a single email digest."""
        from app.core.event_store import event_store
        notifs = event_store.get_queued_notifications()
        if not notifs:
            return
            
        print(f"[EmailNotifier] Compiling digest for {len(notifs)} queued notifications...")
        
        digest_subject = f"NexusAI Notification Digest ({len(notifs)} updates)"
        
        digest_body = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
            <h2 style="color: #06b6d4; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">NexusAI Notification Digest</h2>
            <p style="font-size: 14px; color: #64748b;">Here is a summary of recent lead intelligence updates.</p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        """
        
        for i, notif in enumerate(notifs, 1):
            digest_body += f"""
            <div style="margin-bottom: 30px; padding: 15px; border-left: 4px solid #06b6d4; background-color: #ffffff; border-radius: 4px;">
                <h4 style="margin-top: 0; margin-bottom: 10px; color: #1e293b;">Update #{i}: {notif.get('subject')}</h4>
                <div style="font-size: 13px; color: #334155; line-height: 1.5;">
                    {notif.get('html_content')}
                </div>
            </div>
            """
            
        digest_body += """
            <p style="font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 15px; margin-top: 20px;">
                NexusAI Platform Digest Engine
            </p>
        </div>
        """
        
        # Send the compiled digest
        self.send_notification_raw(digest_subject, digest_body)
        
        # Clear the queue
        event_store.clear_queued_notifications()

    def send_notification_raw(self, subject: str, html_content: str):
        """The actual raw transport layer for sending emails."""
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
                
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                    
                print(f"[EmailNotifier] SMTP notification email sent to {msg['To']} for: {subject}")
            except Exception as e:
                print(f"[EmailNotifier ERROR] SMTP email send failed: {e}")

# Shared notifier instance
notifier = EmailNotifier()
