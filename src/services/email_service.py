"""
Email service for AWS SES integration with template support.
"""

import os
import boto3
import secrets
import string
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError

from ..models.email import EmailType, EmailRequest, EmailResponse
from ..utils.defensive_utils import safe_isoformat
from .logging_service import LoggingService


class EmailService:
    """Service for sending emails via AWS SES with template support."""

    def __init__(self):
        self.ses_client = boto3.client(
            "ses", region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        self.from_email = os.getenv("SES_FROM_EMAIL", "noreply@people-register.local")
        self.frontend_url = os.getenv(
            "FRONTEND_URL", "https://d28z2il3z2vmpc.cloudfront.net"
        )
        self.logger = LoggingService()

    def generate_temporary_password(self, length: int = 12) -> str:
        """Generate a secure temporary password."""
        # Use a mix of letters, digits, and safe special characters
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        # Ensure at least one of each type
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*"),
        ]

        # Fill the rest randomly
        for _ in range(length - 4):
            password.append(secrets.choice(characters))

        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return "".join(password)

    def get_welcome_email_template(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """Get the welcome email template with variables replaced."""

        # Try to read the new enhanced template first
        template_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "registry-infrastructure",
            "email_templates",
            "new_user_welcome_email.html",
        )

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html_template = f.read()
        except FileNotFoundError:
            # Fallback to original template
            template_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "registry-infrastructure",
                "email_templates",
                "welcome_email.html",
            )
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    html_template = f.read()
            except FileNotFoundError:
                # Final fallback template
                html_template = self._get_fallback_welcome_template()

        # Replace variables in the template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            html_template = html_template.replace(placeholder, str(value))

        # Generate plain text version
        text_body = self._html_to_text(html_template, variables)

        return {
            "subject": f"¡Bienvenido! Tu cuenta ha sido creada - {variables.get('project_name', 'AWS User Group Cochabamba')}",
            "html_body": html_template,
            "text_body": text_body,
        }

    def _get_fallback_welcome_template(self) -> str:
        """Fallback welcome email template."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bienvenido al Sistema de Registro</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #161d2b; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">AWS User Group Cochabamba</h1>
            <p style="margin: 5px 0 0 0; color: #FF9900;">Sistema de Registro de Personas</p>
        </div>

        <div style="background: white; padding: 40px; border: 1px solid #ddd;">
            <div style="text-align: center; font-size: 48px; margin-bottom: 20px;">🎉</div>

            <h2 style="color: #161d2b; text-align: center;">¡Bienvenido al Sistema!</h2>

            <p>Hola <strong>{{first_name}} {{last_name}}</strong>,</p>

            <p>¡Gracias por suscribirte a <strong>{{project_name}}</strong>! Tu cuenta ha sido creada exitosamente.</p>

            <div style="background: #f8f9fa; border: 2px solid #e9ecef; border-radius: 8px; padding: 25px; margin: 25px 0;">
                <h3 style="color: #161d2b; text-align: center; margin-top: 0;">Credenciales de Acceso</h3>

                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #4A90E2;">
                    <div style="font-size: 14px; font-weight: 600; color: #666; margin-bottom: 5px;">Email:</div>
                    <div style="font-size: 16px; font-weight: 500; color: #161d2b; font-family: monospace;">{{email}}</div>
                </div>

                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #4A90E2;">
                    <div style="font-size: 14px; font-weight: 600; color: #666; margin-bottom: 5px;">Contraseña Temporal:</div>
                    <div style="font-size: 16px; font-weight: 500; color: #161d2b; font-family: monospace;">{{temporary_password}}</div>
                </div>
            </div>

            <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 20px; margin: 20px 0;">
                <h4 style="color: #856404; margin-top: 0;">⚠️ Importante - Seguridad</h4>
                <p style="color: #856404; margin-bottom: 0;">
                    Esta es una contraseña temporal. Por tu seguridad, debes cambiarla en tu primer inicio de sesión.
                    No compartas estas credenciales con nadie.
                </p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{{login_url}}" style="display: inline-block; padding: 15px 30px; background: #4A90E2; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
                    Iniciar Sesión Ahora
                </a>
            </div>

            <h3>Próximos Pasos:</h3>
            <ol>
                <li><strong>Inicia sesión</strong> usando las credenciales proporcionadas</li>
                <li><strong>Cambia tu contraseña</strong> por una de tu elección</li>
                <li><strong>Completa tu perfil</strong> si es necesario</li>
                <li><strong>Explora los proyectos</strong> disponibles</li>
            </ol>

            <p>Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.</p>

            <p>¡Esperamos verte pronto en nuestros eventos!</p>

            <p style="margin-top: 30px;">
                Saludos,<br>
                <strong>El equipo de AWS User Group Cochabamba</strong>
            </p>
        </div>

        <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef; font-size: 14px; color: #6c757d;">
            <p>Este email fue enviado automáticamente. Por favor no respondas a este mensaje.</p>
            <p>AWS User Group Cochabamba - Sistema de Registro de Personas</p>
        </div>
    </div>
</body>
</html>
        """

    def _html_to_text(self, html_content: str, variables: Dict[str, Any]) -> str:
        """Convert HTML email to plain text version."""
        return f"""
¡Bienvenido al Sistema de Registro!

Hola {variables.get('first_name', '')} {variables.get('last_name', '')},

¡Gracias por suscribirte a {variables.get('project_name', 'nuestro proyecto')}! Tu cuenta ha sido creada exitosamente.

CREDENCIALES DE ACCESO:
Email: {variables.get('email', '')}
Contraseña Temporal: {variables.get('temporary_password', '')}

⚠️ IMPORTANTE - SEGURIDAD:
Esta es una contraseña temporal. Por tu seguridad, debes cambiarla en tu primer inicio de sesión.
No compartas estas credenciales con nadie.

PRÓXIMOS PASOS:
1. Inicia sesión usando las credenciales proporcionadas
2. Cambia tu contraseña por una de tu elección
3. Completa tu perfil si es necesario
4. Explora los proyectos disponibles

Para iniciar sesión, visita: {variables.get('login_url', '')}

Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.

¡Esperamos verte pronto en nuestros eventos!

Saludos,
El equipo de AWS User Group Cochabamba

---
Este email fue enviado automáticamente. Por favor no respondas a este mensaje.
AWS User Group Cochabamba - Sistema de Registro de Personas
        """.strip()

    async def send_welcome_email(
        self,
        email: str,
        first_name: str,
        last_name: str,
        project_name: str,
        temporary_password: str,
    ) -> EmailResponse:
        """Send welcome email with temporary password to new user."""

        variables = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "project_name": project_name,
            "temporary_password": temporary_password,
            "login_url": f"{self.frontend_url}/login",
            "current_year": datetime.now().year,
        }

        template = self.get_welcome_email_template(variables)

        email_request = EmailRequest(
            to_email=email, email_type=EmailType.WELCOME, variables=variables
        )

        return await self.send_email(
            to_email=email,
            subject=template["subject"],
            html_body=template["html_body"],
            text_body=template["text_body"],
            email_type=EmailType.WELCOME,
        )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        email_type: EmailType,
        from_name: str = "AWS User Group Cochabamba",
    ) -> EmailResponse:
        """Send email via AWS SES."""

        try:
            # Prepare the email
            source = f"{from_name} <{self.from_email}>"

            response = self.ses_client.send_email(
                Source=source,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )

            message_id = response["MessageId"]

            # Log the email sending
            await self.logger.log_email_sent(
                recipient=to_email,
                email_type=email_type.value,
                message_id=message_id,
                subject=subject,
            )

            return EmailResponse(
                success=True, message_id=message_id, message="Email sent successfully"
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            await self.logger.log_email_error(
                recipient=to_email,
                email_type=email_type.value,
                error_code=error_code,
                error_message=error_message,
            )

            return EmailResponse(
                success=False,
                error_code=error_code,
                message=f"Failed to send email: {error_message}",
            )

        except Exception as e:
            await self.logger.log_email_error(
                recipient=to_email,
                email_type=email_type.value,
                error_code="UNKNOWN_ERROR",
                error_message=str(e),
            )

            return EmailResponse(
                success=False,
                error_code="UNKNOWN_ERROR",
                message=f"Unexpected error: {str(e)}",
            )

    async def send_password_reset_email(
        self, email: str, first_name: str, reset_token: str, expires_at: datetime
    ) -> EmailResponse:
        """Send password reset email."""

        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
        expires_formatted = expires_at.strftime("%d/%m/%Y a las %H:%M")

        variables = {
            "first_name": first_name,
            "reset_url": reset_url,
            "expires_at": expires_formatted,
            "current_year": datetime.now().year,
        }

        # For now, use a simple template - can be enhanced later
        subject = "Restablecimiento de Contraseña - AWS User Group Cochabamba"

        html_body = f"""
        <h2>Restablecimiento de Contraseña</h2>
        <p>Hola {first_name},</p>
        <p>Recibimos una solicitud para restablecer tu contraseña.</p>
        <p><a href="{reset_url}" style="background: #4A90E2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer Contraseña</a></p>
        <p>Este enlace expira el {expires_formatted}.</p>
        <p>Si no solicitaste este cambio, puedes ignorar este email.</p>
        """

        text_body = f"""
        Restablecimiento de Contraseña

        Hola {first_name},

        Recibimos una solicitud para restablecer tu contraseña.

        Para restablecer tu contraseña, visita: {reset_url}

        Este enlace expira el {expires_formatted}.

        Si no solicitaste este cambio, puedes ignorar este email.
        """

        return await self.send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            email_type=EmailType.PASSWORD_RESET,
        )

    async def send_subscription_approved_email(
        self,
        email: str,
        first_name: str,
        last_name: str,
        project_name: str,
        project_description: Optional[str] = None,
    ) -> EmailResponse:
        """Send subscription approval notification email."""

        variables = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "project_name": project_name,
            "project_description": project_description
            or "Proyecto del AWS User Group Cochabamba",
            "login_url": f"{self.frontend_url}/login",
            "dashboard_url": f"{self.frontend_url}/dashboard",
            "current_year": datetime.now().year,
        }

        subject = f"¡Suscripción Aprobada! - {project_name} - AWS User Group Cochabamba"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #FF9500, #FF6B35); padding: 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 28px;">¡Felicitaciones!</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">Tu suscripción ha sido aprobada</p>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333; margin-top: 0;">Hola {first_name},</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    ¡Excelentes noticias! Tu suscripción al proyecto <strong>{project_name}</strong> 
                    ha sido aprobada por nuestro equipo administrativo.
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FF9500;">
                    <h3 style="color: #333; margin-top: 0;">Detalles del Proyecto:</h3>
                    <p style="margin: 5px 0;"><strong>Proyecto:</strong> {project_name}</p>
                    <p style="margin: 5px 0;"><strong>Descripción:</strong> {project_description}</p>
                    <p style="margin: 5px 0;"><strong>Estado:</strong> <span style="color: #28a745; font-weight: bold;">Activo</span></p>
                </div>
                
                <h3 style="color: #333;">¿Qué sigue?</h3>
                <ul style="color: #555; line-height: 1.6;">
                    <li>Puedes acceder a tu dashboard para ver los detalles del proyecto</li>
                    <li>Recibirás notificaciones sobre actualizaciones y eventos</li>
                    <li>Podrás participar en las actividades programadas</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{variables['dashboard_url']}" 
                       style="background: #FF9500; color: white; padding: 15px 30px; text-decoration: none; 
                              border-radius: 5px; font-weight: bold; display: inline-block;">
                        Acceder al Dashboard
                    </a>
                </div>
                
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    Si tienes alguna pregunta, no dudes en contactarnos.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <div style="text-align: center; color: #999; font-size: 12px;">
                    <p>AWS User Group Cochabamba</p>
                    <p>© {variables['current_year']} Todos los derechos reservados</p>
                </div>
            </div>
        </div>
        """

        text_body = f"""
        ¡Felicitaciones! Tu suscripción ha sido aprobada

        Hola {first_name},

        ¡Excelentes noticias! Tu suscripción al proyecto "{project_name}" ha sido aprobada por nuestro equipo administrativo.

        Detalles del Proyecto:
        - Proyecto: {project_name}
        - Descripción: {project_description}
        - Estado: Activo

        ¿Qué sigue?
        - Puedes acceder a tu dashboard para ver los detalles del proyecto
        - Recibirás notificaciones sobre actualizaciones y eventos
        - Podrás participar en las actividades programadas

        Accede a tu dashboard: {variables['dashboard_url']}

        Si tienes alguna pregunta, no dudes en contactarnos.

        AWS User Group Cochabamba
        © {variables['current_year']} Todos los derechos reservados
        """

        return await self.send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            email_type=EmailType.SUBSCRIPTION_APPROVED,
        )

    async def send_subscription_rejected_email(
        self,
        email: str,
        first_name: str,
        last_name: str,
        project_name: str,
        rejection_reason: Optional[str] = None,
    ) -> EmailResponse:
        """Send subscription rejection notification email."""

        variables = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "project_name": project_name,
            "rejection_reason": rejection_reason
            or "No se proporcionó una razón específica",
            "contact_url": f"{self.frontend_url}/contact",
            "current_year": datetime.now().year,
        }

        subject = (
            f"Actualización de Suscripción - {project_name} - AWS User Group Cochabamba"
        )

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #6c757d, #495057); padding: 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 28px;">Actualización de Suscripción</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">Información sobre tu solicitud</p>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333; margin-top: 0;">Hola {first_name},</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    Gracias por tu interés en el proyecto <strong>{project_name}</strong>. 
                    Después de revisar tu solicitud, lamentamos informarte que no pudimos aprobar 
                    tu suscripción en este momento.
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #6c757d;">
                    <h3 style="color: #333; margin-top: 0;">Detalles:</h3>
                    <p style="margin: 5px 0;"><strong>Proyecto:</strong> {project_name}</p>
                    <p style="margin: 5px 0;"><strong>Estado:</strong> <span style="color: #dc3545; font-weight: bold;">No Aprobado</span></p>
                    <p style="margin: 5px 0;"><strong>Motivo:</strong> {rejection_reason}</p>
                </div>
                
                <h3 style="color: #333;">¿Qué puedes hacer?</h3>
                <ul style="color: #555; line-height: 1.6;">
                    <li>Puedes aplicar a otros proyectos disponibles</li>
                    <li>Contacta con nuestro equipo si tienes preguntas</li>
                    <li>Mantente atento a futuros proyectos que puedan interesarte</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{variables['contact_url']}" 
                       style="background: #6c757d; color: white; padding: 15px 30px; text-decoration: none; 
                              border-radius: 5px; font-weight: bold; display: inline-block;">
                        Contactar Soporte
                    </a>
                </div>
                
                <p style="color: #777; font-size: 14px; margin-top: 30px;">
                    Agradecemos tu interés en participar en nuestras actividades y esperamos 
                    poder contar contigo en futuras oportunidades.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <div style="text-align: center; color: #999; font-size: 12px;">
                    <p>AWS User Group Cochabamba</p>
                    <p>© {variables['current_year']} Todos los derechos reservados</p>
                </div>
            </div>
        </div>
        """

        text_body = f"""
        Actualización de Suscripción

        Hola {first_name},

        Gracias por tu interés en el proyecto "{project_name}". Después de revisar tu solicitud, 
        lamentamos informarte que no pudimos aprobar tu suscripción en este momento.

        Detalles:
        - Proyecto: {project_name}
        - Estado: No Aprobado
        - Motivo: {rejection_reason}

        ¿Qué puedes hacer?
        - Puedes aplicar a otros proyectos disponibles
        - Contacta con nuestro equipo si tienes preguntas
        - Mantente atento a futuros proyectos que puedan interesarte

        Contactar soporte: {variables['contact_url']}

        Agradecemos tu interés en participar en nuestras actividades y esperamos 
        poder contar contigo en futuras oportunidades.

        AWS User Group Cochabamba
        © {variables['current_year']} Todos los derechos reservados
        """

        return await self.send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            email_type=EmailType.SUBSCRIPTION_REJECTED,
        )


# Singleton instance
email_service = EmailService()
