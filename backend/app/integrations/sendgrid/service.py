"""
integrations/sendgrid/service.py
----------------------------------
Transactional email via SendGrid's Web API v3 (plain `requests`, no SDK
dependency needed). This was the missing piece for: purchase receipts,
password-reset emails, and "your agent run failed" notifications -- none
of which should go through Gmail (that's the customer-facing inbox the
agents themselves work out of).

Paste -> backend/app/integrations/sendgrid/service.py

Env vars:
  SENDGRID_API_KEY     <- SendGrid Settings -> API Keys
  SENDGRID_FROM_EMAIL  <- a verified sender (Settings -> Sender Authentication)
  SENDGRID_FROM_NAME   <- optional, defaults to "AgentHub"

If SENDGRID_API_KEY isn't set, send() logs to stdout instead of raising --
so local dev / tests don't need a real SendGrid account to keep running.
"""

import os
import requests

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridService:

    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY", "")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "no-reply@agenthub.local")
        self.from_name = os.getenv("SENDGRID_FROM_NAME", "AgentHub")

    def send(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> dict:
        if not self.api_key:
            print(f"[SendGrid:DEV] Would send '{subject}' to {to_email} (SENDGRID_API_KEY not set)")
            return {"status": "skipped_no_api_key", "to": to_email, "subject": subject}

        content = [{"type": "text/html", "value": html_content}]
        if text_content:
            content.insert(0, {"type": "text/plain", "value": text_content})

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.from_email, "name": self.from_name},
            "subject": subject,
            "content": content,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        r = requests.post(SENDGRID_API_URL, headers=headers, json=payload)
        r.raise_for_status()
        # SendGrid returns 202 with an empty body on success.
        return {"status": "sent", "to": to_email, "subject": subject, "sendgrid_status_code": r.status_code}

    # ------------------------------------------------------------------ #
    # Convenience wrappers for the three cases the platform actually needs
    # ------------------------------------------------------------------ #

    def send_purchase_receipt(self, to_email: str, agent_name: str, monthly_price, business_name: str = "") -> dict:
        subject = f"Receipt: {agent_name} — AgentHub"
        html = f"""
        <h2>Thanks for your purchase!</h2>
        <p>You've installed <strong>{agent_name}</strong>{f' for <strong>{business_name}</strong>' if business_name else ''}.</p>
        <p>Monthly price: <strong>${monthly_price}</strong></p>
        <p>You can manage this agent any time from your AgentHub dashboard.</p>
        """
        return self.send(to_email, subject, html)

    def send_password_reset(self, to_email: str, reset_link: str) -> dict:
        subject = "Reset your AgentHub password"
        html = f"""
        <h2>Password reset requested</h2>
        <p>Click the link below to set a new password. This link expires in 30 minutes.</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """
        return self.send(to_email, subject, html)

    def send_agent_run_failure_alert(self, to_email: str, agent_name: str, business_name: str, error_summary: str) -> dict:
        subject = f"⚠️ {agent_name} failed to run — {business_name}"
        html = f"""
        <h2>An agent run failed</h2>
        <p><strong>{agent_name}</strong> failed while running for <strong>{business_name}</strong>.</p>
        <p><strong>Error:</strong></p>
        <pre style="background:#f4f4f4;padding:12px;border-radius:6px;">{error_summary}</pre>
        <p>Check the Logs tab in your dashboard for the full trace.</p>
        """
        return self.send(to_email, subject, html)
