"""
Task 19: Security Alert Notification Service
Handles security alert notifications and automated responses
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from ..models.security_event import SecurityEvent, SecurityEventType, SecurityEventSeverity
from .email_service import EmailService

class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SNS = "sns"
    SLACK = "slack"
    WEBHOOK = "webhook"

class SecurityAlertService:
    """Service for managing security alerts and notifications"""

    def __init__(self):
        self.email_service = EmailService()
        self.sns_client = boto3.client('sns')
        self.dynamodb = boto3.resource('dynamodb')

        # Initialize tables
        self.audit_logs_table = self.dynamodb.Table('AuditLogsTable')
        self.alert_config_table = self.dynamodb.Table('AlertConfigTable')  # Would need to be created

        # Alert thresholds
        self.alert_thresholds = {
            'failed_logins_per_hour': 10,
            'failed_logins_per_ip_per_hour': 5,
            'password_resets_per_hour': 5,
            'account_lockouts_per_hour': 3,
            'suspicious_activity_threshold': 1
        }

        # Admin notification emails (would be configurable)
        self.admin_emails = [
            'security@people-register.local',
            'admin@people-register.local'
        ]

    def process_security_event(self, event: SecurityEvent) -> bool:
        """Process a security event and trigger alerts if necessary"""
        try:
            # Check if event should trigger alerts
            should_alert = self._should_trigger_alert(event)

            if should_alert:
                # Create alert
                alert = self._create_alert_from_event(event)

                # Send notifications
                self._send_alert_notifications(alert)

                # Check for automated responses
                self._check_automated_responses(event)

            return True

        except Exception as e:
            print(f"Error processing security event: {str(e)}")
            return False

    def _should_trigger_alert(self, event: SecurityEvent) -> bool:
        """Determine if a security event should trigger an alert"""

        # Always alert on critical events
        if event.severity == SecurityEventSeverity.CRITICAL:
            return True

        # Always alert on high severity events
        if event.severity == SecurityEventSeverity.HIGH:
            return True

        # Check specific event types
        if event.event_type == SecurityEventType.BRUTE_FORCE_ATTEMPT:
            return True

        if event.event_type == SecurityEventType.ACCOUNT_LOCKED:
            return True

        if event.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY:
            return True

        # Check for patterns (multiple events of same type)
        if self._check_event_patterns(event):
            return True

        return False

    def _check_event_patterns(self, event: SecurityEvent) -> bool:
        """Check for concerning patterns in security events"""
        try:
            # Check for multiple failed logins from same IP
            if event.event_type == SecurityEventType.LOGIN_FAILED and event.ip_address:
                recent_failures = self._get_recent_events_by_ip(
                    event.ip_address,
                    SecurityEventType.LOGIN_FAILED,
                    hours=1
                )
                if len(recent_failures) >= self.alert_thresholds['failed_logins_per_ip_per_hour']:
                    return True

            # Check for multiple password resets
            if event.event_type == SecurityEventType.PASSWORD_RESET_REQUESTED:
                recent_resets = self._get_recent_events_by_type(
                    SecurityEventType.PASSWORD_RESET_REQUESTED,
                    hours=1
                )
                if len(recent_resets) >= self.alert_thresholds['password_resets_per_hour']:
                    return True

            # Check for multiple account lockouts
            if event.event_type == SecurityEventType.ACCOUNT_LOCKED:
                recent_lockouts = self._get_recent_events_by_type(
                    SecurityEventType.ACCOUNT_LOCKED,
                    hours=1
                )
                if len(recent_lockouts) >= self.alert_thresholds['account_lockouts_per_hour']:
                    return True

            return False

        except Exception as e:
            print(f"Error checking event patterns: {str(e)}")
            return False

    def _get_recent_events_by_ip(self, ip_address: str, event_type: SecurityEventType, hours: int = 1) -> List[Dict]:
        """Get recent events from specific IP address"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            response = self.audit_logs_table.scan(
                FilterExpression='ipAddress = :ip AND eventType = :event_type AND #ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':ip': ip_address,
                    ':event_type': event_type.value,
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )

            return response.get('Items', [])

        except Exception as e:
            print(f"Error getting recent events by IP: {str(e)}")
            return []

    def _get_recent_events_by_type(self, event_type: SecurityEventType, hours: int = 1) -> List[Dict]:
        """Get recent events of specific type"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            response = self.audit_logs_table.scan(
                FilterExpression='eventType = :event_type AND #ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':event_type': event_type.value,
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )

            return response.get('Items', [])

        except Exception as e:
            print(f"Error getting recent events by type: {str(e)}")
            return []

    def _create_alert_from_event(self, event: SecurityEvent) -> Dict[str, Any]:
        """Create alert data structure from security event"""

        alert_titles = {
            SecurityEventType.BRUTE_FORCE_ATTEMPT: "Brute Force Attack Detected",
            SecurityEventType.ACCOUNT_LOCKED: "User Account Locked",
            SecurityEventType.SUSPICIOUS_ACTIVITY: "Suspicious Activity Detected",
            SecurityEventType.LOGIN_FAILED: "Multiple Failed Login Attempts",
            SecurityEventType.PASSWORD_RESET_REQUESTED: "High Volume Password Reset Requests",
            SecurityEventType.RATE_LIMIT_EXCEEDED: "Rate Limit Exceeded",
        }

        alert_messages = {
            SecurityEventType.BRUTE_FORCE_ATTEMPT: f"Brute force attack detected from IP {event.ip_address}",
            SecurityEventType.ACCOUNT_LOCKED: f"User account {event.user_email} has been locked due to failed login attempts",
            SecurityEventType.SUSPICIOUS_ACTIVITY: f"Suspicious activity detected for user {event.user_email}",
            SecurityEventType.LOGIN_FAILED: f"Multiple failed login attempts detected from IP {event.ip_address}",
            SecurityEventType.PASSWORD_RESET_REQUESTED: "High volume of password reset requests detected",
            SecurityEventType.RATE_LIMIT_EXCEEDED: f"Rate limit exceeded from IP {event.ip_address}",
        }

        return {
            'id': f"alert-{event.id}",
            'title': alert_titles.get(event.event_type, f"Security Event: {event.event_type.value}"),
            'message': alert_messages.get(event.event_type, f"Security event detected: {event.event_type.value}"),
            'severity': event.severity.value,
            'event_type': event.event_type.value,
            'timestamp': event.timestamp.isoformat(),
            'user_email': event.user_email,
            'ip_address': event.ip_address,
            'details': event.details,
            'action_required': event.severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL],
            'acknowledged': False
        }

    def _send_alert_notifications(self, alert: Dict[str, Any]):
        """Send alert notifications through configured channels"""
        try:
            # Send email notifications
            self._send_email_alert(alert)

            # Send SNS notifications (if configured)
            self._send_sns_alert(alert)

            # Log alert
            print(f"🚨 SECURITY ALERT SENT: {alert['title']} - {alert['severity']}")

        except Exception as e:
            print(f"Error sending alert notifications: {str(e)}")

    def _send_email_alert(self, alert: Dict[str, Any]):
        """Send email alert to administrators"""
        try:
            subject = f"🚨 Security Alert: {alert['title']}"

            # Create HTML email content
            html_content = f"""
            <html>
            <body>
                <h2 style="color: #dc2626;">Security Alert</h2>
                <div style="background-color: #fef2f2; padding: 20px; border-left: 4px solid #dc2626; margin: 20px 0;">
                    <h3>{alert['title']}</h3>
                    <p><strong>Severity:</strong> <span style="color: #dc2626; text-transform: uppercase;">{alert['severity']}</span></p>
                    <p><strong>Time:</strong> {alert['timestamp']}</p>
                    <p><strong>Message:</strong> {alert['message']}</p>

                    {f"<p><strong>User:</strong> {alert['user_email']}</p>" if alert['user_email'] else ""}
                    {f"<p><strong>IP Address:</strong> {alert['ip_address']}</p>" if alert['ip_address'] else ""}

                    {f"<p><strong>Action Required:</strong> Yes</p>" if alert['action_required'] else ""}
                </div>

                <h4>Recommended Actions:</h4>
                <ul>
                    <li>Review the security dashboard for additional context</li>
                    <li>Check for related security events</li>
                    <li>Consider blocking suspicious IP addresses</li>
                    <li>Monitor affected user accounts</li>
                </ul>

                <p><em>This is an automated security alert from the People Register system.</em></p>
            </body>
            </html>
            """

            # Send to all admin emails
            for admin_email in self.admin_emails:
                self.email_service.send_email(
                    to_email=admin_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=f"Security Alert: {alert['title']}\n\n{alert['message']}\n\nSeverity: {alert['severity']}\nTime: {alert['timestamp']}"
                )

        except Exception as e:
            print(f"Error sending email alert: {str(e)}")

    def _send_sns_alert(self, alert: Dict[str, Any]):
        """Send SNS alert notification"""
        try:
            # This would be configured with actual SNS topic ARN
            sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:security-alerts"

            message = {
                'default': f"Security Alert: {alert['title']}",
                'email': f"Security Alert: {alert['title']}\n\n{alert['message']}\n\nSeverity: {alert['severity']}\nTime: {alert['timestamp']}",
                'sms': f"Security Alert: {alert['title']} - {alert['severity']}"
            }

            # Uncomment when SNS is configured
            # self.sns_client.publish(
            #     TopicArn=sns_topic_arn,
            #     Message=json.dumps(message),
            #     MessageStructure='json',
            #     Subject=f"Security Alert: {alert['title']}"
            # )

            print(f"SNS alert would be sent: {alert['title']}")

        except Exception as e:
            print(f"Error sending SNS alert: {str(e)}")

    def _check_automated_responses(self, event: SecurityEvent):
        """Check if automated responses should be triggered"""
        try:
            # Auto-block IP after multiple brute force attempts
            if event.event_type == SecurityEventType.BRUTE_FORCE_ATTEMPT and event.ip_address:
                self._consider_ip_blocking(event.ip_address)

            # Auto-disable account after suspicious activity
            if event.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY and event.user_id:
                self._consider_account_suspension(event.user_id)

        except Exception as e:
            print(f"Error checking automated responses: {str(e)}")

    def _consider_ip_blocking(self, ip_address: str):
        """Consider blocking an IP address"""
        try:
            # Check recent brute force attempts from this IP
            recent_attempts = self._get_recent_events_by_ip(
                ip_address,
                SecurityEventType.BRUTE_FORCE_ATTEMPT,
                hours=1
            )

            if len(recent_attempts) >= 3:  # Threshold for auto-blocking
                print(f"🚫 IP {ip_address} should be blocked (automated response)")

                # In production, this would:
                # 1. Add IP to WAF block list
                # 2. Update security groups
                # 3. Log the automated action
                # 4. Notify administrators

        except Exception as e:
            print(f"Error considering IP blocking: {str(e)}")

    def _consider_account_suspension(self, user_id: str):
        """Consider suspending a user account"""
        try:
            # This would implement logic to temporarily suspend suspicious accounts
            print(f"⚠️ User {user_id} account should be reviewed for suspension")

            # In production, this would:
            # 1. Temporarily disable the account
            # 2. Require admin review before re-enabling
            # 3. Send notification to user and admins
            # 4. Log the automated action

        except Exception as e:
            print(f"Error considering account suspension: {str(e)}")

    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics for dashboard"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # This would query alert history
            # For now, return placeholder data
            return {
                'total_alerts': 0,
                'critical_alerts': 0,
                'high_alerts': 0,
                'medium_alerts': 0,
                'low_alerts': 0,
                'alerts_by_type': {},
                'recent_alerts': []
            }

        except Exception as e:
            print(f"Error getting alert statistics: {str(e)}")
            return {}

    def acknowledge_alert(self, alert_id: str, admin_email: str) -> bool:
        """Acknowledge a security alert"""
        try:
            # This would update alert status in database
            print(f"Alert {alert_id} acknowledged by {admin_email}")
            return True

        except Exception as e:
            print(f"Error acknowledging alert: {str(e)}")
            return False
