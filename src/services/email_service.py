"""
Email service for AWS SES integration.
Clean implementation for the new API architecture.
"""

import os
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

from ..core.config import config


class EmailService:
    """Service for sending emails via AWS SES."""

    def __init__(self):
        # Check if we're in test mode
        self.test_mode = os.getenv("EMAIL_TEST_MODE", "false").lower() in [
            "true",
            "1",
            "yes",
        ]

        # Initialize SES client (unless in test mode)
        if not self.test_mode:
            self.ses_client = boto3.client("ses", region_name=config.email.region)
        else:
            self.ses_client = None

        self.from_email = config.email.from_email
        self.frontend_url = config.frontend_url

    async def send_password_reset_email(
        self, email: str, first_name: str, reset_token: str
    ) -> Dict[str, Any]:
        """Send password reset email."""

        if self.test_mode:
            return {
                "success": True,
                "message": "Email would be sent (TEST MODE)",
                "message_id": "test-mode-message-id",
            }

        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"

        subject = "Restablecimiento de Contraseña - AWS User Group Cochabamba"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #161d2b; color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">AWS User Group Cochabamba</h1>
                <p style="margin: 5px 0 0 0; color: #FF9900;">Restablecimiento de Contraseña</p>
            </div>

            <div style="background: white; padding: 40px; border: 1px solid #ddd;">
                <h2 style="color: #161d2b;">Hola {first_name},</h2>

                <p>Recibimos una solicitud para restablecer tu contraseña.</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}"
                       style="display: inline-block; padding: 15px 30px; background: #4A90E2;
                              color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
                        Restablecer Contraseña
                    </a>
                </div>

                <p><strong>Este enlace expira en 1 hora.</strong></p>

                <p>Si no solicitaste este cambio, puedes ignorar este email.</p>

                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de AWS User Group Cochabamba</strong>
                </p>
            </div>

            <div style="background: #f8f9fa; padding: 20px; text-align: center;
                        border-top: 1px solid #e9ecef; font-size: 14px; color: #6c757d;">
                <p>Este email fue enviado automáticamente. Por favor no respondas a este mensaje.</p>
            </div>
        </div>
        """

        text_body = f"""
        Restablecimiento de Contraseña

        Hola {first_name},

        Recibimos una solicitud para restablecer tu contraseña.

        Para restablecer tu contraseña, visita: {reset_url}

        Este enlace expira en 1 hora.

        Si no solicitaste este cambio, puedes ignorar este email.

        Saludos,
        El equipo de AWS User Group Cochabamba
        """

        try:
            response = self.ses_client.send_email(
                Source=f"AWS User Group Cochabamba <{self.from_email}>",
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )

            return {
                "success": True,
                "message": "Password reset email sent successfully",
                "message_id": response["MessageId"],
            }

        except ClientError as e:
            return {
                "success": False,
                "message": f"Failed to send email: {e.response['Error']['Message']}",
                "error_code": e.response["Error"]["Code"],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "error_code": "UNKNOWN_ERROR",
            }

    async def send_subscription_notification_email(
        self, email: str, first_name: str, project_name: str, status: str
    ) -> Dict[str, Any]:
        """Send subscription status notification email."""

        if self.test_mode:
            return {
                "success": True,
                "message": "Email would be sent (TEST MODE)",
                "message_id": "test-mode-message-id",
            }

        if status == "approved":
            subject = f"¡Suscripción Aprobada! - {project_name}"
            message = f"¡Felicitaciones! Tu suscripción al proyecto {project_name} ha sido aprobada."
            color = "#28a745"
        else:
            subject = f"Actualización de Suscripción - {project_name}"
            message = f"Tu suscripción al proyecto {project_name} ha sido actualizada."
            color = "#6c757d"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">AWS User Group Cochabamba</h1>
                <p style="margin: 5px 0 0 0;">Actualización de Suscripción</p>
            </div>

            <div style="background: white; padding: 40px; border: 1px solid #ddd;">
                <h2 style="color: #161d2b;">Hola {first_name},</h2>

                <p>{message}</p>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Proyecto:</strong> {project_name}</p>
                    <p><strong>Estado:</strong> {status.title()}</p>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.frontend_url}/dashboard"
                       style="display: inline-block; padding: 15px 30px; background: {color};
                              color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
                        Ver Dashboard
                    </a>
                </div>

                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de AWS User Group Cochabamba</strong>
                </p>
            </div>
        </div>
        """

        try:
            response = self.ses_client.send_email(
                Source=f"AWS User Group Cochabamba <{self.from_email}>",
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                    },
                },
            )

            return {
                "success": True,
                "message": "Subscription notification email sent successfully",
                "message_id": response["MessageId"],
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
            }
