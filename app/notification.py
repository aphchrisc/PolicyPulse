"""
notification.py

Notification system for PolicyPulse that sends alerts to users about relevant legislation
based on their preferences and configured thresholds.
"""


import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.enums import NotificationTypeEnum
from app.models import (User, AlertPreference, AlertHistory, Legislation,
                     LegislationPriority)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NotificationManager:
    """
    Manages notifications for the PolicyPulse application.
    
    Responsible for processing and sending notifications to users based on 
    their preferences and alert thresholds for legislation updates.
    """

    def __init__(self,
                 db_session: Session,
                 smtp_config: Optional[Dict] = None):
        """
        Initialize the notification manager.
        
        Args:
            db_session: SQLAlchemy session for database access.
            smtp_config: Optional configuration for SMTP. If not provided, defaults to environment variables.
        """
        self.db_session = db_session
        self.smtp_config = smtp_config or {
            "server": os.environ.get("SMTP_SERVER", "smtp.example.com"),
            "port": int(os.environ.get("SMTP_PORT", "587")),
            "username": os.environ.get("SMTP_USERNAME", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
            "from_email": os.environ.get("SMTP_FROM", "notifications@policypulse.org"),
        }

    def process_pending_notifications(self) -> Dict[str, int]:
        """
        Process all pending notifications based on user preferences.
        
        Returns:
            A dictionary with statistics about the notifications processed.
        """
        stats = {
            "high_priority": 0,
            "new_bill": 0,
            "status_change": 0,
            "analysis_complete": 0,
            "errors": 0,
            "total": 0
        }

        # Retrieve users with active alert preferences
        users = self.db_session.query(User).join(
            AlertPreference,
            and_(User.id == AlertPreference.user_id,
                 AlertPreference.active)).all()

        for user in users:
            try:
                # Initialize to zero before processing
                new_alerts = 0
                analysis_alerts = 0
                high_priority_alerts = 0

                # Process new legislation alerts if enabled
                if user.alert_preferences.notify_on_new:
                    new_alerts = self._process_new_legislation_alerts(user)
                    stats["new_bill"] += new_alerts

                # Process analysis complete alerts if enabled
                if user.alert_preferences.notify_on_analysis:
                    analysis_alerts = self._process_analysis_alerts(user)
                    stats["analysis_complete"] += analysis_alerts

                # Process high priority alerts (always on)
                high_priority_alerts = self._process_high_priority_alerts(user)
                stats["high_priority"] += high_priority_alerts

                # Update total notifications sent
                stats[
                    "total"] += new_alerts + analysis_alerts + high_priority_alerts

            except (ValueError, KeyError, AttributeError) as e:
                logger.error(
                    "Error processing notifications for user %s: %s",
                    str(user.email), str(e)
                )
                stats["errors"] += 1

        return stats

    def _process_high_priority_alerts(self, user: User) -> int:
        """
        Process high priority legislation alerts for a user.
        
        Args:
            user: The user for whom to process alerts.
            
        Returns:
            Number of high priority notifications sent.
        """
        count = 0

        # Determine the threshold for high priority based on the user's preferences
        high_priority_threshold = user.alert_preferences.health_threshold
        recent_high_priority = self.db_session.query(Legislation).join(
            LegislationPriority,
            and_(
                Legislation.id == LegislationPriority.legislation_id,
                or_(
                    LegislationPriority.public_health_relevance
                    >= high_priority_threshold,
                    LegislationPriority.overall_priority
                    >= high_priority_threshold),
                LegislationPriority.should_notify,
                LegislationPriority.notification_sent)).limit(10).all()

        if recent_high_priority:
            # Send notification for high priority legislation
            count = self._send_legislation_notification(
                user=user,
                legislation_list=recent_high_priority,
                notification_type=NotificationTypeEnum.high_priority,
                subject="High Priority Legislation Alert",
                _template_name="high_priority_alert.html")

            # Mark each legislation as having been notified
            for leg in recent_high_priority:
                leg.priority.notification_sent = True
                leg.priority.notification_date = datetime.now(timezone.utc)

            self.db_session.commit()

        return count

    def _process_new_legislation_alerts(self, user: User) -> int:
        """
        Process alerts for new legislation for a user.
        
        Args:
            user: The user for whom to process alerts.
            
        Returns:
            Number of new legislation notifications sent.
        """
        # Get legislation created within the last 24 hours that matches user interests
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        new_legislation = self.db_session.query(Legislation).filter(
            Legislation.created_at >= cutoff_time,
            Legislation.categories.overlap(user.interests)
        ).limit(10).all()
        
        if new_legislation:
            return self._send_legislation_notification(
                user=user,
                legislation_list=new_legislation,
                notification_type=NotificationTypeEnum.new_bill,
                subject="New Legislation Alert",
                _template_name="new_legislation_alert.html")
        return 0

    def _process_analysis_alerts(self, user: User) -> int:
        """
        Process alerts for completed analyses for a user.
        
        Args:
            user: The user for whom to process alerts.
            
        Returns:
            Number of analysis complete notifications sent.
        """
        # Get legislation with recently completed analysis that matches user interests
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        analyzed_legislation = self.db_session.query(Legislation).filter(
            Legislation.analysis_completed_at >= cutoff_time,
            Legislation.analysis_completed_at.isnot(None),
            Legislation.categories.overlap(user.interests)
        ).limit(10).all()
        
        if analyzed_legislation:
            return self._send_legislation_notification(
                user=user,
                legislation_list=analyzed_legislation,
                notification_type=NotificationTypeEnum.analysis_complete,
                subject="Legislation Analysis Complete",
                _template_name="analysis_complete_alert.html")
        return 0

    def _send_legislation_notification(self, user: User,
                                       legislation_list: List[Legislation],
                                       notification_type: NotificationTypeEnum,
                                       subject: str, _template_name: str) -> int:
        """
        Send a notification about legislation to a user.
        
        Args:
            user: The user to notify.
            legislation_list: List of legislation records to include in the notification.
            notification_type: The type of notification.
            subject: The email subject.
            _template_name: The template name to use (for future integration with a templating engine).
            
        Returns:
            The number of notifications sent (0 or 1).
        """
        if not legislation_list:
            return 0

        try:
            return self._process_legislation_notification(
                user, subject, legislation_list, notification_type
            )
        except (smtplib.SMTPException, ValueError, IOError) as e:
            logger.error("Error sending notification to %s: %s", str(user.email), str(e))
            self.db_session.rollback()
            return 0

    def _process_legislation_notification(self, user, subject, legislation_list, notification_type):
        # Check if the user has email notifications enabled
        channels = user.alert_preferences.alert_channels or {"email": True}
        if not channels.get("email", True):
            return 0

        # Build a simple HTML email content
        email_content = f"<h1>{subject}</h1><ul>"
        for leg in legislation_list:
            email_content += f"<li><strong>{str(leg.bill_number)}</strong>: {str(leg.title)}</li>"
        email_content += "</ul><p>Visit PolicyPulse for more details.</p>"

        # Send the email using SMTP
        self._send_email(recipient=str(user.email),
                         subject=subject,
                         html_content=email_content)

        # Record the notification in the alert history
        for leg in legislation_list:
            alert_history = AlertHistory(
                user_id=user.id,
                legislation_id=leg.id,
                alert_type=notification_type,
                alert_content=f"{str(leg.bill_number)}: {str(leg.title)}",
                delivery_status="sent")
            self.db_session.add(alert_history)

        self.db_session.commit()
        return 1

    def _send_email(self, recipient: str, subject: str,
                    html_content: str) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            recipient: The email recipient.
            subject: The email subject.
            html_content: The HTML content of the email.
            
        Returns:
            True if the email was sent successfully; False otherwise.
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_config["from_email"]
            msg['To'] = recipient

            # Attach the HTML content to the email
            msg.attach(MIMEText(html_content, 'html'))

            # Connect to the SMTP server, initiate TLS, log in if credentials provided, and send the email
            with smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"]) as server:
                server.starttls()
                if self.smtp_config["username"] and self.smtp_config["password"]:
                    server.login(self.smtp_config["username"], self.smtp_config["password"])
                server.send_message(msg)

            return True

        except (smtplib.SMTPException, ConnectionError) as e:
            logger.error("Error sending email to %s: %s", recipient, str(e))
            return False
