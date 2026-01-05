"""
PhotonPath - Email Service v2
=============================

Supporte SMTP ET Resend API (pour les plateformes qui bloquent SMTP).

Configuration .env:
    # Option 1: Resend API (recommandé pour Railway/Vercel)
    RESEND_API_KEY=re_xxxxx
    EMAIL_FROM=PhotonPath <noreply@banastechnologie.cloud>
    
    # Option 2: SMTP (si pas bloqué)
    SMTP_HOST=ssl0.ovh.net
    SMTP_PORT=587
    SMTP_USER=contact@banastechnologie.cloud
    SMTP_PASSWORD=xxx

Author: PhotonPath
"""

import os
from typing import Optional
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class EmailConfig:
    """Email configuration."""
    provider: str  # "resend" or "smtp"
    api_key: Optional[str] = None
    from_email: str = "contact@banastechnologie.cloud"
    from_name: str = "PhotonPath"
    # SMTP specific
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


def get_email_config() -> Optional[EmailConfig]:
    """Load email configuration from environment."""
    
    # Priority 1: Resend API
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        return EmailConfig(
            provider="resend",
            api_key=resend_key,
            from_email=os.getenv("EMAIL_FROM", "PhotonPath <contact@banastechnologie.cloud>"),
            from_name=os.getenv("EMAIL_FROM_NAME", "PhotonPath")
        )
    
    # Priority 2: SMTP
    smtp_host = os.getenv("SMTP_HOST")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if smtp_host and smtp_password:
        return EmailConfig(
            provider="smtp",
            smtp_host=smtp_host,
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER"),
            smtp_password=smtp_password,
            from_email=os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER")),
            from_name=os.getenv("SMTP_FROM_NAME", "PhotonPath")
        )
    
    return None


# Pour compatibilité avec l'ancien code
def get_smtp_config():
    """Backward compatibility."""
    config = get_email_config()
    if config and config.provider == "smtp":
        class SMTPConfig:
            pass
        c = SMTPConfig()
        c.host = config.smtp_host
        c.port = config.smtp_port
        c.user = config.smtp_user
        c.password = config.smtp_password
        c.from_email = config.from_email
        c.from_name = config.from_name
        return c
    elif config and config.provider == "resend":
        class SMTPConfig:
            pass
        c = SMTPConfig()
        c.host = "api.resend.com"
        c.port = 443
        c.from_email = config.from_email
        c.from_name = config.from_name
        return c
    return None


# ============================================================================
# EMAIL SERVICE
# ============================================================================

class EmailService:
    """Service d'envoi d'emails multi-provider."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or get_email_config()
        self.enabled = self.config is not None
        
        if self.enabled:
            print(f"✅ Email service initialized ({self.config.provider})")
        else:
            print("⚠️ Email service disabled (no config)")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Envoie un email via le provider configuré."""
        
        if not self.enabled:
            print(f"📧 [MOCK] Email to {to_email}: {subject}")
            return True
        
        if self.config.provider == "resend":
            return self._send_via_resend(to_email, subject, html_content)
        else:
            return self._send_via_smtp(to_email, subject, html_content, text_content)
    
    def _send_via_resend(self, to_email: str, subject: str, html_content: str) -> bool:
        """Envoie via Resend API."""
        try:
            import urllib.request
            import json
            
            data = {
                "from": self.config.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps(data).encode('utf-8'),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                print(f"✅ Email sent via Resend to {to_email}: {result.get('id')}")
                return True
                
        except Exception as e:
            print(f"❌ Resend error: {e}")
            return False
    
    def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Envoie via SMTP."""
        try:
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import re
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = to_email
            
            if text_content is None:
                text_content = re.sub(r'<[^>]+>', '', html_content)
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            if self.config.smtp_port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, context=context) as server:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                    server.sendmail(self.config.from_email, to_email, msg.as_string())
            else:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.starttls()
                    server.login(self.config.smtp_user, self.config.smtp_password)
                    server.sendmail(self.config.from_email, to_email, msg.as_string())
            
            print(f"✅ Email sent via SMTP to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ SMTP error: {e}")
            return False
    
    # ========================================================================
    # TEMPLATES
    # ========================================================================
    
    def _get_email_header(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f4f7fa; line-height: 1.6;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f7fa;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                            <tr>
                                <td align="center" style="padding-bottom: 30px;">
                                    <span style="font-size: 28px; font-weight: 700; color: #1a1a2e;">⚡ PhotonPath</span>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08); overflow: hidden;">
        """
    
    def _get_email_footer(self) -> str:
        return """
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="padding-top: 30px;">
                                    <p style="margin: 0; font-size: 13px; color: #8896a6;">© 2025 PhotonPath by BanasTechnologie</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def send_welcome_email(self, to_email: str, api_key: str) -> bool:
        """Email de bienvenue."""
        subject = "🚀 Bienvenue sur PhotonPath - Votre clé API"
        
        html = self._get_email_header() + f"""
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #00d4aa 0%, #7c3aed 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">🎉 Bienvenue !</h1>
                                                <p style="margin: 10px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">Votre compte PhotonPath est prêt</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Merci de rejoindre PhotonPath ! Votre compte est maintenant <strong style="color: #00d4aa;">actif</strong>.
                                                </p>
                                                
                                                <div style="background: #f0fdf4; border: 2px solid #00d4aa; border-radius: 12px; padding: 20px; margin: 25px 0;">
                                                    <p style="margin: 0 0 10px 0; font-size: 12px; font-weight: 600; color: #059669; text-transform: uppercase;">🔑 Votre Clé API</p>
                                                    <p style="margin: 0; font-family: monospace; font-size: 14px; color: #065f46; background: #fff; padding: 12px; border-radius: 8px; word-break: break-all;">
                                                        {api_key}
                                                    </p>
                                                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #6b7280;">⚠️ Gardez cette clé secrète !</p>
                                                </div>
                                                
                                                <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin: 25px 0;">
                                                    <p style="margin: 0 0 10px 0; font-size: 14px; font-weight: 600; color: #1e293b;">⚡ Quick Start</p>
                                                    <code style="display: block; font-size: 12px; color: #10b981; background: #1e293b; padding: 12px; border-radius: 8px;">
                                                        curl -H "X-API-Key: YOUR_KEY" \\<br>
                                                        &nbsp;&nbsp;https://photonpath-api-production.up.railway.app/v2/tissues
                                                    </code>
                                                </div>
                                                
                                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                    <tr>
                                                        <td align="center" style="padding: 20px 0;">
                                                            <a href="https://photonpath-api-production.up.railway.app/docs" 
                                                               style="display: inline-block; padding: 14px 35px; background: linear-gradient(135deg, #00d4aa, #7c3aed); color: #fff; font-weight: 600; text-decoration: none; border-radius: 10px;">
                                                                📖 Documentation
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)
    
    def send_subscription_activated(self, to_email: str, plan: str, api_key: str) -> bool:
        """Email confirmation abonnement."""
        plan_info = {
            "spark": {"name": "Spark", "emoji": "🔬", "price": "Gratuit"},
            "photon": {"name": "Photon", "emoji": "💡", "price": "29€/mois"},
            "beam": {"name": "Beam", "emoji": "🔦", "price": "99€/mois"},
            "laser": {"name": "Laser", "emoji": "⚡", "price": "299€/mois"},
            "fusion": {"name": "Fusion", "emoji": "🌟", "price": "Sur devis"}
        }
        info = plan_info.get(plan, plan_info["spark"])
        
        subject = f"✅ Abonnement {info['name']} activé - PhotonPath"
        
        html = self._get_email_header() + f"""
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #10b981, #059669); padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 28px; color: #fff;">✅ Abonnement Activé !</h1>
                                                <p style="margin: 10px 0 0 0; font-size: 18px; color: rgba(255,255,255,0.9);">{info['emoji']} Plan {info['name']}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Votre abonnement <strong>{info['name']}</strong> ({info['price']}) est actif !
                                                </p>
                                                
                                                <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 12px; padding: 20px; margin: 25px 0;">
                                                    <p style="margin: 0 0 10px 0; font-size: 12px; font-weight: 600; color: #b45309; text-transform: uppercase;">🔑 Nouvelle Clé API</p>
                                                    <p style="margin: 0; font-family: monospace; font-size: 14px; color: #92400e; background: #fff; padding: 12px; border-radius: 8px; word-break: break-all;">
                                                        {api_key}
                                                    </p>
                                                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #92400e;">⚠️ Cette clé remplace l'ancienne !</p>
                                                </div>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)
    
    def send_subscription_cancelled(self, to_email: str) -> bool:
        """Email annulation."""
        subject = "😢 Abonnement annulé - PhotonPath"
        
        html = self._get_email_header() + """
                                        <tr>
                                            <td style="background: #6b7280; padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 28px; color: #fff;">Abonnement Annulé</h1>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Votre abonnement a été annulé. Vous êtes maintenant sur le plan <strong>Spark (gratuit)</strong>.
                                                </p>
                                                <p style="color: #6b7280;">Vous pouvez réactiver à tout moment.</p>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)
    
    def send_payment_failed(self, to_email: str) -> bool:
        """Email échec paiement."""
        subject = "⚠️ Échec de paiement - PhotonPath"
        
        html = self._get_email_header() + """
                                        <tr>
                                            <td style="background: #ef4444; padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 28px; color: #fff;">⚠️ Échec de Paiement</h1>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Nous n'avons pas pu traiter votre paiement. Veuillez mettre à jour vos informations.
                                                </p>
                                                <p style="color: #ef4444;">Votre accès risque d'être suspendu.</p>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)


# ============================================================================
# SINGLETON
# ============================================================================

_email_service: Optional[EmailService] = None

def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

def init_email_service() -> EmailService:
    global _email_service
    _email_service = EmailService()
    return _email_service


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 50)
    print("📧 Test Email Service")
    print("=" * 50)
    
    service = init_email_service()
    
    if service.enabled:
        print(f"\n✅ Provider: {service.config.provider}")
        if service.config.provider == "resend":
            print(f"   API Key: {service.config.api_key[:10]}...")
        else:
            print(f"   SMTP: {service.config.smtp_host}:{service.config.smtp_port}")
    else:
        print("\n⚠️ Email not configured")
        print("   Set RESEND_API_KEY or SMTP_* variables")