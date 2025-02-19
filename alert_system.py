import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import os

class AlertSystem:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get("SMTP_EMAIL")
        self.sender_password = os.environ.get("SMTP_PASSWORD")

    def update_email(self, email: str) -> bool:
        """Update user's email for alerts"""
        # In a real application, this would validate and store the email
        return True

    def send_alert(self, recipient_email: str, legislation_updates: List[Dict]) -> bool:
        """Send email alert about new legislation"""
        try:
            if not legislation_updates:
                return True

            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = "New Legislation Alert - Congress Monitor"

            body = self._format_email_body(legislation_updates)
            message.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            return True
        except Exception as e:
            print(f"Error sending alert: {e}")
            return False

    def _format_email_body(self, legislation_updates: List[Dict]) -> str:
        """Format the email body with legislation updates"""
        html = """
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>New Legislation Updates</h2>
                <p>The following new legislation items may be relevant to your interests:</p>
        """

        for bill in legislation_updates:
            html += f"""
                <div style="margin-bottom: 20px; padding: 10px; border-left: 4px solid #0066cc;">
                    <h3>{bill['number']}: {bill['title']}</h3>
                    <p><strong>Status:</strong> {bill['status']}</p>
                    <p><strong>Introduced:</strong> {bill['introduced_date']}</p>
                    <p><a href="{bill['url']}">View Full Text</a></p>
                </div>
            """

        html += """
            </body>
        </html>
        """
        return html
