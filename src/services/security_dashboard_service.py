"""
Task 19: Security Dashboard Service
Provides security monitoring and dashboard data for administrators
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from decimal import Decimal

from .dynamodb_service import DynamoDBService
from ..models.security_event import SecurityEvent, SecurityEventType
from ..utils.date_utils import format_datetime, parse_datetime

class SecurityDashboardService:
    """Service for admin security dashboard and monitoring"""

    def __init__(self):
        self.db_service = DynamoDBService()
        self.dynamodb = boto3.resource('dynamodb')

        # Initialize tables
        self.audit_logs_table = self.dynamodb.Table('AuditLogsTable')
        self.people_table = self.dynamodb.Table('PeopleTable')
        self.password_reset_tokens_table = self.dynamodb.Table('PasswordResetTokensTable')
        self.session_tracking_table = self.dynamodb.Table('SessionTrackingTable')

    def get_security_overview(self, days: int = 7) -> Dict[str, Any]:
        """Get security overview for the dashboard"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        overview = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'failed_logins': self._get_failed_login_stats(start_date, end_date),
            'password_resets': self._get_password_reset_stats(start_date, end_date),
            'account_lockouts': self._get_account_lockout_stats(start_date, end_date),
            'security_events': self._get_security_event_stats(start_date, end_date),
            'active_sessions': self._get_active_session_stats(),
            'user_activity': self._get_user_activity_stats(start_date, end_date)
        }

        return overview

    def _get_failed_login_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get failed login attempt statistics"""
        try:
            # Query audit logs for failed login attempts
            response = self.audit_logs_table.scan(
                FilterExpression=(Attr('eventType').eq('FAILED_LOGIN')
                                  & Attr('timestamp').between(start_date.isoformat(), end_date.isoformat()))
            )

            failed_logins = response.get('Items', [])

            # Group by day
            daily_stats = {}
            email_stats = {}
            ip_stats = {}

            for event in failed_logins:
                # Daily grouping
                event_date = parse_datetime(event['timestamp']).date().isoformat()
                daily_stats[event_date] = daily_stats.get(event_date, 0) + 1

                # Email grouping
                email = event.get('userEmail', 'unknown')
                email_stats[email] = email_stats.get(email, 0) + 1

                # IP grouping
                ip = event.get('ipAddress', 'unknown')
                ip_stats[ip] = ip_stats.get(ip, 0) + 1

            return {
                'total_count': len(failed_logins),
                'daily_breakdown': daily_stats,
                'top_failed_emails': sorted(email_stats.items(), key=lambda x: x[1], reverse=True)[:10],
                'top_failed_ips': sorted(ip_stats.items(), key=lambda x: x[1], reverse=True)[:10],
                'recent_events': sorted(failed_logins, key=lambda x: x['timestamp'], reverse=True)[:20]
            }

        except Exception as e:
            print(f"Error getting failed login stats: {str(e)}")
            return {'total_count': 0, 'daily_breakdown': {}, 'top_failed_emails': [], 'top_failed_ips': [], 'recent_events': []}

    def _get_password_reset_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get password reset request statistics"""
        try:
            # Query password reset tokens
            response = self.password_reset_tokens_table.scan(
                FilterExpression=Attr('createdAt').between(start_date.isoformat(), end_date.isoformat())
            )

            reset_requests = response.get('Items', [])

            # Group by day and status
            daily_stats = {}
            status_stats = {'requested': 0, 'completed': 0, 'expired': 0}
            email_stats = {}

            current_time = datetime.utcnow()

            for request in reset_requests:
                # Daily grouping
                request_date = parse_datetime(request['createdAt']).date().isoformat()
                daily_stats[request_date] = daily_stats.get(request_date, 0) + 1

                # Status grouping
                if request.get('isUsed', False):
                    status_stats['completed'] += 1
                elif parse_datetime(request['expiresAt']) < current_time:
                    status_stats['expired'] += 1
                else:
                    status_stats['requested'] += 1

                # Email grouping
                email = request.get('email', 'unknown')
                email_stats[email] = email_stats.get(email, 0) + 1

            return {
                'total_count': len(reset_requests),
                'daily_breakdown': daily_stats,
                'status_breakdown': status_stats,
                'top_reset_emails': sorted(email_stats.items(), key=lambda x: x[1], reverse=True)[:10],
                'recent_requests': sorted(reset_requests, key=lambda x: x['createdAt'], reverse=True)[:20]
            }

        except Exception as e:
            print(f"Error getting password reset stats: {str(e)}")
            return {'total_count': 0, 'daily_breakdown': {}, 'status_breakdown': {}, 'top_reset_emails': [], 'recent_requests': []}

    def _get_account_lockout_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get account lockout statistics"""
        try:
            # Query for locked accounts
            response = self.people_table.scan(
                FilterExpression=Attr('failedLoginAttempts').gte(5) | Attr('isActive').eq(False)
            )

            locked_accounts = response.get('Items', [])

            # Query audit logs for lockout events
            lockout_events_response = self.audit_logs_table.scan(
                FilterExpression=(Attr('eventType').eq('ACCOUNT_LOCKED')
                                  & Attr('timestamp').between(start_date.isoformat(), end_date.isoformat()))
            )

            lockout_events = lockout_events_response.get('Items', [])

            # Group by day
            daily_lockouts = {}
            for event in lockout_events:
                event_date = parse_datetime(event['timestamp']).date().isoformat()
                daily_lockouts[event_date] = daily_lockouts.get(event_date, 0) + 1

            return {
                'currently_locked_count': len([acc for acc in locked_accounts if not acc.get('isActive', True)]),
                'high_failed_attempts_count': len([acc for acc in locked_accounts if acc.get('failedLoginAttempts', 0) >= 5]),
                'lockout_events_count': len(lockout_events),
                'daily_lockouts': daily_lockouts,
                'locked_accounts': [
                    {
                        'id': acc['id'],
                        'email': acc['email'],
                        'failedLoginAttempts': acc.get('failedLoginAttempts', 0),
                        'isActive': acc.get('isActive', True),
                        'lockedUntil': acc.get('lockedUntil')
                    }
                    for acc in locked_accounts
                ],
                'recent_lockout_events': sorted(lockout_events, key=lambda x: x['timestamp'], reverse=True)[:10]
            }

        except Exception as e:
            print(f"Error getting account lockout stats: {str(e)}")
            return {'currently_locked_count': 0, 'high_failed_attempts_count': 0, 'lockout_events_count': 0, 'daily_lockouts': {}, 'locked_accounts': [], 'recent_lockout_events': []}

    def _get_security_event_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get general security event statistics"""
        try:
            # Query all security events
            response = self.audit_logs_table.scan(
                FilterExpression=Attr('timestamp').between(start_date.isoformat(), end_date.isoformat())
            )

            events = response.get('Items', [])

            # Group by event type
            event_type_stats = {}
            severity_stats = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            daily_events = {}

            for event in events:
                # Event type grouping
                event_type = event.get('eventType', 'UNKNOWN')
                event_type_stats[event_type] = event_type_stats.get(event_type, 0) + 1

                # Severity grouping
                severity = event.get('severity', 'low')
                severity_stats[severity] = severity_stats.get(severity, 0) + 1

                # Daily grouping
                event_date = parse_datetime(event['timestamp']).date().isoformat()
                daily_events[event_date] = daily_events.get(event_date, 0) + 1

            return {
                'total_events': len(events),
                'event_type_breakdown': event_type_stats,
                'severity_breakdown': severity_stats,
                'daily_events': daily_events,
                'recent_high_severity': [
                    event for event in sorted(events, key=lambda x: x['timestamp'], reverse=True)
                    if event.get('severity') in ['high', 'critical']
                ][:10]
            }

        except Exception as e:
            print(f"Error getting security event stats: {str(e)}")
            return {'total_events': 0, 'event_type_breakdown': {}, 'severity_breakdown': {}, 'daily_events': {}, 'recent_high_severity': []}

    def _get_active_session_stats(self) -> Dict[str, Any]:
        """Get active session statistics"""
        try:
            # Query active sessions
            response = self.session_tracking_table.scan(
                FilterExpression=Attr('isActive').eq(True)
            )

            active_sessions = response.get('Items', [])

            # Group by device and location
            device_stats = {}
            user_stats = {}

            for session in active_sessions:
                # Device grouping
                device_info = session.get('deviceInfo', 'Unknown Device')
                device_stats[device_info] = device_stats.get(device_info, 0) + 1

                # User grouping
                user_id = session.get('userId', 'unknown')
                user_stats[user_id] = user_stats.get(user_id, 0) + 1

            return {
                'total_active_sessions': len(active_sessions),
                'device_breakdown': device_stats,
                'users_with_multiple_sessions': len([user for user, count in user_stats.items() if count > 1]),
                'recent_sessions': sorted(active_sessions, key=lambda x: x.get('lastActivity', x.get('createdAt', '')), reverse=True)[:20]
            }

        except Exception as e:
            print(f"Error getting active session stats: {str(e)}")
            return {'total_active_sessions': 0, 'device_breakdown': {}, 'users_with_multiple_sessions': 0, 'recent_sessions': []}

    def _get_user_activity_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get user activity statistics"""
        try:
            # Query login events
            response = self.audit_logs_table.scan(
                FilterExpression=(Attr('eventType').eq('LOGIN_SUCCESS')
                                  & Attr('timestamp').between(start_date.isoformat(), end_date.isoformat()))
            )

            login_events = response.get('Items', [])

            # Group by user and day
            user_activity = {}
            daily_logins = {}

            for event in login_events:
                # User activity
                user_email = event.get('userEmail', 'unknown')
                if user_email not in user_activity:
                    user_activity[user_email] = {'login_count': 0, 'last_login': None}

                user_activity[user_email]['login_count'] += 1
                event_time = event['timestamp']
                if not user_activity[user_email]['last_login'] or event_time > user_activity[user_email]['last_login']:
                    user_activity[user_email]['last_login'] = event_time

                # Daily logins
                event_date = parse_datetime(event['timestamp']).date().isoformat()
                daily_logins[event_date] = daily_logins.get(event_date, 0) + 1

            return {
                'total_logins': len(login_events),
                'unique_users': len(user_activity),
                'daily_logins': daily_logins,
                'most_active_users': sorted(
                    [(email, data['login_count'], data['last_login']) for email, data in user_activity.items()],
                    key=lambda x: x[1], reverse=True
                )[:10]
            }

        except Exception as e:
            print(f"Error getting user activity stats: {str(e)}")
            return {'total_logins': 0, 'unique_users': 0, 'daily_logins': {}, 'most_active_users': []}

    def get_security_alerts(self, severity: str = 'medium') -> List[Dict[str, Any]]:
        """Get security alerts based on severity"""
        try:
            # Query high-severity events from last 24 hours
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)

            response = self.audit_logs_table.scan(
                FilterExpression=(Attr('severity').gte(severity)
                                  & Attr('timestamp').between(start_date.isoformat(), end_date.isoformat()))
            )

            alerts = response.get('Items', [])

            # Sort by timestamp (most recent first)
            alerts.sort(key=lambda x: x['timestamp'], reverse=True)

            return alerts

        except Exception as e:
            print(f"Error getting security alerts: {str(e)}")
            return []

    def create_security_event(self, event_type: str, user_email: str = None,
                              ip_address: str = None, details: Dict[str, Any] = None,
                              severity: str = 'medium') -> bool:
        """Create a new security event for monitoring"""
        try:
            event_id = f"security-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{hash(str(details))}"

            event_data = {
                'id': event_id,
                'eventType': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'severity': severity,
                'ipAddress': ip_address,
                'userEmail': user_email,
                'details': details or {},
                'processed': False
            }

            self.audit_logs_table.put_item(Item=event_data)

            # If high severity, trigger immediate alert
            if severity in ['high', 'critical']:
                self._trigger_security_alert(event_data)

            return True

        except Exception as e:
            print(f"Error creating security event: {str(e)}")
            return False

    def _trigger_security_alert(self, event_data: Dict[str, Any]):
        """Trigger immediate security alert for high-severity events"""
        try:
            # This would integrate with SNS, email service, or other alerting systems
            print(f"🚨 SECURITY ALERT: {event_data['eventType']} - {event_data['severity']}")
            print(f"Details: {json.dumps(event_data, indent=2)}")

            # In production, this would:
            # 1. Send email to security team
            # 2. Create SNS notification
            # 3. Log to security monitoring system
            # 4. Potentially trigger automated responses

        except Exception as e:
            print(f"Error triggering security alert: {str(e)}")

    def get_failed_login_details(self, email: str = None, ip_address: str = None,
                                 hours: int = 24) -> List[Dict[str, Any]]:
        """Get detailed failed login attempts for specific user or IP"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=hours)

            filter_expression = (Attr('eventType').eq('FAILED_LOGIN')
                                 & Attr('timestamp').between(start_date.isoformat(), end_date.isoformat()))

            if email:
                filter_expression = filter_expression & Attr('userEmail').eq(email)

            if ip_address:
                filter_expression = filter_expression & Attr('ipAddress').eq(ip_address)

            response = self.audit_logs_table.scan(FilterExpression=filter_expression)

            failed_logins = response.get('Items', [])
            failed_logins.sort(key=lambda x: x['timestamp'], reverse=True)

            return failed_logins

        except Exception as e:
            print(f"Error getting failed login details: {str(e)}")
            return []

    def unlock_user_account(self, user_id: str, admin_email: str) -> bool:
        """Unlock a user account (admin action)"""
        try:
            # Reset failed login attempts and activate account
            self.people_table.update_item(
                Key={'id': user_id},
                UpdateExpression='SET failedLoginAttempts = :zero, isActive = :active, lockedUntil = :null',
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':active': True,
                    ':null': None
                }
            )

            # Log admin action
            self.create_security_event(
                event_type='ADMIN_ACCOUNT_UNLOCK',
                user_email=admin_email,
                details={'unlocked_user_id': user_id},
                severity='medium'
            )

            return True

        except Exception as e:
            print(f"Error unlocking user account: {str(e)}")
            return False
