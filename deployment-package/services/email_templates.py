"""
Email templates for the People Register system.
"""

from typing import Dict, Any
from ..models.email import EmailType


class EmailTemplates:
    """Email template generator for various notification types."""

    @staticmethod
    def get_password_reset_template(data: Dict[str, Any]) -> Dict[str, str]:
        """Generate password reset email template."""

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .button:hover {{ background: #5a6fd8; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {data.get('first_name', 'User')},</h2>

                    <p>We received a request to reset your password for your People Register account. If you made this request, click the button below to reset your password:</p>

                    <div style="text-align: center;">
                        <a href="{data.get('reset_link', '#')}" class="button">Reset My Password</a>
                    </div>

                    <div class="warning">
                        <strong>⚠️ Important Security Information:</strong>
                        <ul>
                            <li>This link will expire in {data.get('expiry_hours', 1)} hour(s)</li>
                            <li>This link can only be used once</li>
                            <li>If you didn't request this reset, please ignore this email</li>
                        </ul>
                    </div>

                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 3px;">
                        {data.get('reset_link', '#')}
                    </p>

                    <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>

                    <p>For security reasons, we recommend:</p>
                    <ul>
                        <li>Using a strong, unique password</li>
                        <li>Not sharing your password with anyone</li>
                        <li>Logging out of shared computers</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Need help? Contact us at <a href="mailto:{data.get('support_email', 'support@people-register.local')}">{data.get('support_email', 'support@people-register.local')}</a></p>
                    <p>© 2024 People Register. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Password Reset Request - People Register

        Hello {data.get('first_name', 'User')},

        We received a request to reset your password for your People Register account.

        To reset your password, please visit this link:
        {data.get('reset_link', '#')}

        IMPORTANT SECURITY INFORMATION:
        - This link will expire in {data.get('expiry_hours', 1)} hour(s)
        - This link can only be used once
        - If you didn't request this reset, please ignore this email

        If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

        For security reasons, we recommend:
        - Using a strong, unique password
        - Not sharing your password with anyone
        - Logging out of shared computers

        Need help? Contact us at {data.get('support_email', 'support@people-register.local')}

        © 2024 People Register. All rights reserved.
        """

        return {"html_body": html_body, "text_body": text_body}

    @staticmethod
    def get_password_changed_template(data: Dict[str, Any]) -> Dict[str, str]:
        """Generate password changed confirmation email template."""

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Changed Successfully</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00b894 0%, #00a085 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .info-box {{ background: #e3f2fd; border: 1px solid #bbdefb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Password Changed Successfully</h1>
                </div>
                <div class="content">
                    <h2>Hello {data.get('first_name', 'User')},</h2>

                    <div class="success">
                        <strong>✅ Your password has been successfully changed!</strong>
                    </div>

                    <p>This email confirms that your People Register account password was changed on {data.get('change_time', 'recently')}.</p>

                    <div class="info-box">
                        <strong>📋 Change Details:</strong>
                        <ul>
                            <li><strong>Date & Time:</strong> {data.get('change_time', 'Recently')}</li>
                            <li><strong>IP Address:</strong> {data.get('ip_address', 'Not available')}</li>
                        </ul>
                    </div>

                    <p><strong>If you made this change:</strong></p>
                    <ul>
                        <li>No further action is required</li>
                        <li>Your account is secure</li>
                        <li>You can continue using People Register normally</li>
                    </ul>

                    <p><strong>If you did NOT make this change:</strong></p>
                    <ul>
                        <li>Your account may have been compromised</li>
                        <li>Contact our support team immediately</li>
                        <li>Consider changing passwords on other accounts that use the same password</li>
                    </ul>

                    <p>For your security, we recommend:</p>
                    <ul>
                        <li>Using unique passwords for each account</li>
                        <li>Enabling two-factor authentication when available</li>
                        <li>Regularly updating your passwords</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Need help? Contact us at <a href="mailto:{data.get('support_email', 'support@people-register.local')}">{data.get('support_email', 'support@people-register.local')}</a></p>
                    <p>© 2024 People Register. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Password Changed Successfully - People Register

        Hello {data.get('first_name', 'User')},

        This email confirms that your People Register account password was changed on {data.get('change_time', 'recently')}.

        CHANGE DETAILS:
        - Date & Time: {data.get('change_time', 'Recently')}
        - IP Address: {data.get('ip_address', 'Not available')}

        If you made this change:
        - No further action is required
        - Your account is secure
        - You can continue using People Register normally

        If you did NOT make this change:
        - Your account may have been compromised
        - Contact our support team immediately at {data.get('support_email', 'support@people-register.local')}
        - Consider changing passwords on other accounts that use the same password

        For your security, we recommend:
        - Using unique passwords for each account
        - Enabling two-factor authentication when available
        - Regularly updating your passwords

        Need help? Contact us at {data.get('support_email', 'support@people-register.local')}

        © 2024 People Register. All rights reserved.
        """

        return {"html_body": html_body, "text_body": text_body}

    @staticmethod
    def get_password_reset_confirmation_template(
        data: Dict[str, Any],
    ) -> Dict[str, str]:
        """Generate password reset confirmation email template."""

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00b894 0%, #00a085 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Successful</h1>
                </div>
                <div class="content">
                    <h2>Hello {data.get('first_name', 'User')},</h2>

                    <div class="success">
                        <strong>✅ Your password has been successfully reset!</strong>
                    </div>

                    <p>This email confirms that you have successfully reset your People Register account password using the secure reset link.</p>

                    <p><strong>What happens next:</strong></p>
                    <ul>
                        <li>You can now log in with your new password</li>
                        <li>All existing sessions have been logged out for security</li>
                        <li>The reset link you used is no longer valid</li>
                    </ul>

                    <p>For your security, we recommend:</p>
                    <ul>
                        <li>Keep your new password secure and don't share it</li>
                        <li>Use a unique password that you don't use elsewhere</li>
                        <li>Log out of shared or public computers</li>
                    </ul>

                    <p>If you did not reset your password, please contact our support team immediately.</p>
                </div>
                <div class="footer">
                    <p>Need help? Contact us at <a href="mailto:{data.get('support_email', 'support@people-register.local')}">{data.get('support_email', 'support@people-register.local')}</a></p>
                    <p>© 2024 People Register. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Password Reset Successful - People Register

        Hello {data.get('first_name', 'User')},

        This email confirms that you have successfully reset your People Register account password using the secure reset link.

        What happens next:
        - You can now log in with your new password
        - All existing sessions have been logged out for security
        - The reset link you used is no longer valid

        For your security, we recommend:
        - Keep your new password secure and don't share it
        - Use a unique password that you don't use elsewhere
        - Log out of shared or public computers

        If you did not reset your password, please contact our support team immediately at {data.get('support_email', 'support@people-register.local')}.

        Need help? Contact us at {data.get('support_email', 'support@people-register.local')}

        © 2024 People Register. All rights reserved.
        """

        return {"html_body": html_body, "text_body": text_body}

    @staticmethod
    def get_email_verification_template(data: Dict[str, Any]) -> Dict[str, str]:
        """Generate email verification template for new email address."""

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your New Email Address</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .button:hover {{ background: #5a6fd8; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .info-box {{ background: #e3f2fd; border: 1px solid #bbdefb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📧 Verify Your New Email Address</h1>
                </div>
                <div class="content">
                    <h2>Hello {data.get('first_name', 'User')},</h2>

                    <p>You've requested to change your email address for your People Register account. To complete this change, please verify your new email address by clicking the button below:</p>

                    <div style="text-align: center;">
                        <a href="{data.get('verification_link', '#')}" class="button">Verify New Email Address</a>
                    </div>

                    <div class="info-box">
                        <strong>📋 Email Change Details:</strong>
                        <ul>
                            <li><strong>Current Email:</strong> {data.get('current_email', 'Not available')}</li>
                            <li><strong>New Email:</strong> {data.get('new_email', 'This email address')}</li>
                        </ul>
                    </div>

                    <div class="warning">
                        <strong>⚠️ Important Information:</strong>
                        <ul>
                            <li>This verification link will expire in 24 hours</li>
                            <li>This link can only be used once</li>
                            <li>Your current email address will remain active until verification is complete</li>
                            <li>If you didn't request this change, please ignore this email</li>
                        </ul>
                    </div>

                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 3px;">
                        {data.get('verification_link', '#')}
                    </p>

                    <p>Once verified, this email address will become your new login email for People Register.</p>
                </div>
                <div class="footer">
                    <p>Need help? Contact us at <a href="mailto:{data.get('support_email', 'support@people-register.local')}">{data.get('support_email', 'support@people-register.local')}</a></p>
                    <p>© 2024 People Register. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Verify Your New Email Address - People Register

        Hello {data.get('first_name', 'User')},

        You've requested to change your email address for your People Register account. To complete this change, please verify your new email address by visiting this link:

        {data.get('verification_link', '#')}

        EMAIL CHANGE DETAILS:
        - Current Email: {data.get('current_email', 'Not available')}
        - New Email: {data.get('new_email', 'This email address')}

        IMPORTANT INFORMATION:
        - This verification link will expire in 24 hours
        - This link can only be used once
        - Your current email address will remain active until verification is complete
        - If you didn't request this change, please ignore this email

        Once verified, this email address will become your new login email for People Register.

        Need help? Contact us at {data.get('support_email', 'support@people-register.local')}

        © 2024 People Register. All rights reserved.
        """

        return {"html_body": html_body, "text_body": text_body}

    @staticmethod
    def get_email_change_notification_template(data: Dict[str, Any]) -> Dict[str, str]:
        """Generate email change notification template for current email address."""

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Change Request Notification</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .info-box {{ background: #e3f2fd; border: 1px solid #bbdefb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .button {{ display: inline-block; background: #e67e22; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .button:hover {{ background: #d35400; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 Email Change Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {data.get('first_name', 'User')},</h2>

                    <p>We're writing to inform you that a request has been made to change the email address associated with your People Register account.</p>

                    <div class="info-box">
                        <strong>📋 Change Request Details:</strong>
                        <ul>
                            <li><strong>Current Email:</strong> {data.get('current_email', 'This email address')}</li>
                            <li><strong>Requested New Email:</strong> {data.get('new_email', 'Not available')}</li>
                            <li><strong>Request Time:</strong> {data.get('change_time', 'Recently')}</li>
                        </ul>
                    </div>

                    <p><strong>If you made this request:</strong></p>
                    <ul>
                        <li>A verification email has been sent to your new email address</li>
                        <li>You must verify the new email address to complete the change</li>
                        <li>Your current email address will remain active until verification is complete</li>
                        <li>No further action is required from this email address</li>
                    </ul>

                    <div class="warning">
                        <strong>⚠️ If you did NOT make this request:</strong>
                        <ul>
                            <li>Your account may be compromised</li>
                            <li>Contact our support team immediately</li>
                            <li>Consider changing your password</li>
                            <li>The email change will not complete without verification</li>
                        </ul>
                    </div>

                    <p>You can also verify the new email address using this link if you have access to it:</p>
                    <div style="text-align: center;">
                        <a href="{data.get('verification_link', '#')}" class="button">Verify New Email</a>
                    </div>

                    <p>For your security, we recommend:</p>
                    <ul>
                        <li>Regularly reviewing your account settings</li>
                        <li>Using strong, unique passwords</li>
                        <li>Monitoring your account for unauthorized changes</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Need help? Contact us at <a href="mailto:{data.get('support_email', 'support@people-register.local')}">{data.get('support_email', 'support@people-register.local')}</a></p>
                    <p>© 2024 People Register. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Email Change Request Notification - People Register

        Hello {data.get('first_name', 'User')},

        We're writing to inform you that a request has been made to change the email address associated with your People Register account.

        CHANGE REQUEST DETAILS:
        - Current Email: {data.get('current_email', 'This email address')}
        - Requested New Email: {data.get('new_email', 'Not available')}
        - Request Time: {data.get('change_time', 'Recently')}

        If you made this request:
        - A verification email has been sent to your new email address
        - You must verify the new email address to complete the change
        - Your current email address will remain active until verification is complete
        - No further action is required from this email address

        If you did NOT make this request:
        - Your account may be compromised
        - Contact our support team immediately at {data.get('support_email', 'support@people-register.local')}
        - Consider changing your password
        - The email change will not complete without verification

        You can also verify the new email address using this link if you have access to it:
        {data.get('verification_link', '#')}

        For your security, we recommend:
        - Regularly reviewing your account settings
        - Using strong, unique passwords
        - Monitoring your account for unauthorized changes

        Need help? Contact us at {data.get('support_email', 'support@people-register.local')}

        © 2024 People Register. All rights reserved.
        """

        return {"html_body": html_body, "text_body": text_body}

    @staticmethod
    def get_template(email_type: EmailType, data: Dict[str, Any]) -> Dict[str, str]:
        """Get email template by type."""

        template_map = {
            EmailType.PASSWORD_RESET: EmailTemplates.get_password_reset_template,
            EmailType.PASSWORD_CHANGED: EmailTemplates.get_password_changed_template,
            EmailType.PASSWORD_RESET_CONFIRMATION: EmailTemplates.get_password_reset_confirmation_template,
            EmailType.EMAIL_VERIFICATION: EmailTemplates.get_email_verification_template,
            EmailType.EMAIL_CHANGE_NOTIFICATION: EmailTemplates.get_email_change_notification_template,
        }

        template_func = template_map.get(email_type)
        if not template_func:
            raise ValueError(f"Template not found for email type: {email_type}")

        return template_func(data)
