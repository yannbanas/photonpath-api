"""
PhotonPath - Email Service v3
=============================

Supporte SMTP ET Resend API avec templates professionnels.

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
    from_email: str = "noreply@banastechnologie.cloud"
    from_name: str = "PhotonPath"
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


def get_email_config() -> Optional[EmailConfig]:
    """Load email configuration from environment."""
    
    # Priority 1: Resend API
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        from_email = os.getenv("EMAIL_FROM", "PhotonPath <noreply@banastechnologie.cloud>")
        return EmailConfig(
            provider="resend",
            api_key=resend_key.strip(),
            from_email=from_email,
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


def get_smtp_config():
    """Backward compatibility."""
    config = get_email_config()
    if config:
        class SMTPConfig:
            pass
        c = SMTPConfig()
        c.host = config.smtp_host or "api.resend.com"
        c.port = config.smtp_port or 443
        c.from_email = config.from_email
        c.from_name = config.from_name
        return c
    return None


# ============================================================================
# EMAIL SERVICE
# ============================================================================

class EmailService:
    """Service d'envoi d'emails multi-provider avec templates pro."""
    
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
            
            with urllib.request.urlopen(req, timeout=15) as response:
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
    # EMAIL TEMPLATES - DESIGN CLAIR
    # ========================================================================
    
    def send_welcome_email(self, to_email: str, api_key: str) -> bool:
        """📧 Email de bienvenue avec clé API - Design clair."""
        
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bienvenue sur PhotonPath</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f7fa; line-height: 1.6;">
    
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f7fa;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                    
                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 25px;">
                            <span style="font-size: 26px; font-weight: 700; color: #1a1a2e;">⚡ <span style="color: #0891b2;">Photon</span><span style="color: #1a1a2e;">Path</span></span>
                        </td>
                    </tr>
                    
                    <!-- Main Card -->
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);">
                                
                                <!-- Header Gradient -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #06b6d4 0%, #8b5cf6 50%, #ec4899 100%); padding: 40px 30px; text-align: center;">
                                        <div style="font-size: 42px; margin-bottom: 10px;">🎉</div>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">Bienvenue !</h1>
                                        <p style="margin: 8px 0 0 0; font-size: 15px; color: rgba(255,255,255,0.9);">Votre compte PhotonPath est prêt</p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 35px 30px;">
                                        
                                        <p style="margin: 0 0 25px 0; font-size: 15px; color: #4a5568; line-height: 1.7;">
                                            Merci de rejoindre PhotonPath ! Votre compte est maintenant <strong style="color: #10b981;">actif</strong> et prêt à utiliser.
                                        </p>
                                        
                                        <!-- API Key Box -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
                                            <tr>
                                                <td style="background: #f0fdf4; border: 2px solid #10b981; border-radius: 12px; padding: 20px;">
                                                    <p style="margin: 0 0 10px 0; font-size: 11px; font-weight: 700; color: #059669; text-transform: uppercase; letter-spacing: 1px;">
                                                        🔑 VOTRE CLÉ API
                                                    </p>
                                                    <p style="margin: 0; font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace; font-size: 13px; color: #065f46; background: #ffffff; padding: 14px; border-radius: 8px; word-break: break-all; border: 1px solid #d1fae5;">
                                                        {api_key}
                                                    </p>
                                                    <p style="margin: 12px 0 0 0; font-size: 12px; color: #ca8a04;">
                                                        ⚠️ Gardez cette clé secrète ! Ne la partagez jamais publiquement.
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Quick Start Code -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
                                            <tr>
                                                <td style="background: #1e293b; border-radius: 12px; padding: 20px;">
                                                    <p style="margin: 0 0 12px 0; font-size: 13px; font-weight: 600; color: #e2e8f0;">
                                                        ⚡ Démarrage rapide
                                                    </p>
                                                    <div style="font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace; font-size: 12px; line-height: 1.8;">
                                                        <p style="margin: 0; color: #64748b;"># Python</p>
                                                        <p style="margin: 0;"><span style="color: #c084fc;">import</span> <span style="color: #22d3ee;">requests</span></p>
                                                        <p style="margin: 10px 0 0 0;"><span style="color: #e2e8f0;">response</span> <span style="color: #64748b;">=</span> <span style="color: #22d3ee;">requests</span><span style="color: #e2e8f0;">.</span><span style="color: #fbbf24;">get</span><span style="color: #e2e8f0;">(</span></p>
                                                        <p style="margin: 0; padding-left: 20px;"><span style="color: #a5f3fc;">"https://photonpath-api-production.up.railway.app/v2/tissues"</span><span style="color: #e2e8f0;">,</span></p>
                                                        <p style="margin: 0; padding-left: 20px;"><span style="color: #e2e8f0;">headers=</span><span style="color: #fbbf24;">{{"X-API-Key"</span><span style="color: #e2e8f0;">:</span> <span style="color: #a5f3fc;">"VOTRE_CLÉ_API"</span><span style="color: #fbbf24;">}}</span></p>
                                                        <p style="margin: 0;"><span style="color: #e2e8f0;">)</span></p>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- CTA Button -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding: 20px 0;">
                                                    <a href="https://photonpath-api-production.up.railway.app/docs" 
                                                       style="display: inline-block; padding: 14px 40px; background: linear-gradient(135deg, #06b6d4, #0891b2); color: #ffffff; font-weight: 600; text-decoration: none; border-radius: 10px; font-size: 14px; box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);">
                                                        📖 Voir la Documentation
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Plan Info -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top: 20px; border-top: 1px solid #e5e7eb; padding-top: 20px;">
                                            <tr>
                                                <td width="50%">
                                                    <p style="margin: 0 0 5px 0; font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px;">Plan actuel</p>
                                                    <p style="margin: 0; font-size: 14px; color: #1f2937; font-weight: 600;">🔬 Spark (Gratuit)</p>
                                                </td>
                                                <td width="50%">
                                                    <p style="margin: 0 0 5px 0; font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px;">Limites</p>
                                                    <p style="margin: 0; font-size: 14px; color: #1f2937; font-weight: 600;">100 req/jour</p>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 30px;">
                            <p style="margin: 0; font-size: 13px; color: #6b7280;">© 2025 PhotonPath by BanasTechnologie</p>
                            <p style="margin: 5px 0 0 0; font-size: 12px; color: #9ca3af;">API Biophotonique pour la Recherche</p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
    
</body>
</html>
"""
        
        return self.send_email(to_email, "🚀 Bienvenue sur PhotonPath - Votre clé API", html)
    
    def send_subscription_activated(self, to_email: str, plan: str, api_key: str) -> bool:
        """📧 Email confirmation abonnement."""
        
        plan_info = {
            "spark": {"name": "Spark", "emoji": "🔬", "price": "Gratuit", "requests": "100"},
            "photon": {"name": "Photon", "emoji": "💡", "price": "29€/mois", "requests": "2,000"},
            "beam": {"name": "Beam", "emoji": "🔦", "price": "99€/mois", "requests": "15,000"},
            "laser": {"name": "Laser", "emoji": "⚡", "price": "299€/mois", "requests": "100,000"},
            "fusion": {"name": "Fusion", "emoji": "🌟", "price": "Sur devis", "requests": "Illimité"}
        }
        info = plan_info.get(plan, plan_info["spark"])
        
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f4f7fa; line-height: 1.6;">
    
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f7fa;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                    
                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 25px;">
                            <span style="font-size: 26px; font-weight: 700; color: #1a1a2e;">⚡ <span style="color: #0891b2;">Photon</span><span style="color: #1a1a2e;">Path</span></span>
                        </td>
                    </tr>
                    
                    <!-- Main Card -->
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 30px; text-align: center;">
                                        <div style="font-size: 42px; margin-bottom: 10px;">✅</div>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">Abonnement Activé !</h1>
                                        <p style="margin: 8px 0 0 0; font-size: 15px; color: rgba(255,255,255,0.9);">{info['emoji']} Plan {info['name']} - {info['price']}</p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 35px 30px;">
                                        
                                        <p style="margin: 0 0 25px 0; font-size: 15px; color: #4a5568; line-height: 1.7;">
                                            Votre abonnement <strong style="color: #059669;">{info['name']}</strong> est maintenant actif ! 
                                            Profitez de <strong>{info['requests']} requêtes/jour</strong>.
                                        </p>
                                        
                                        <!-- New API Key Box -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
                                            <tr>
                                                <td style="background: #fefce8; border: 2px solid #eab308; border-radius: 12px; padding: 20px;">
                                                    <p style="margin: 0 0 10px 0; font-size: 11px; font-weight: 700; color: #a16207; text-transform: uppercase; letter-spacing: 1px;">
                                                        🔑 NOUVELLE CLÉ API
                                                    </p>
                                                    <p style="margin: 0; font-family: monospace; font-size: 13px; color: #854d0e; background: #ffffff; padding: 14px; border-radius: 8px; word-break: break-all; border: 1px solid #fef08a;">
                                                        {api_key}
                                                    </p>
                                                    <p style="margin: 12px 0 0 0; font-size: 12px; color: #dc2626;">
                                                        ⚠️ Cette clé remplace votre ancienne clé !
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- CTA -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding: 20px 0;">
                                                    <a href="https://photonpath-api-production.up.railway.app/docs" 
                                                       style="display: inline-block; padding: 14px 40px; background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; font-weight: 600; text-decoration: none; border-radius: 10px; font-size: 14px;">
                                                        🚀 Commencer à utiliser l'API
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 30px;">
                            <p style="margin: 0; font-size: 13px; color: #6b7280;">© 2025 PhotonPath by BanasTechnologie</p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
    
</body>
</html>
"""
        
        return self.send_email(to_email, f"✅ Abonnement {info['name']} activé - PhotonPath", html)
    
    def send_subscription_cancelled(self, to_email: str) -> bool:
        """📧 Email annulation."""
        
        html = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f4f7fa; line-height: 1.6;">
    
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f7fa;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                    
                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 25px;">
                            <span style="font-size: 26px; font-weight: 700; color: #1a1a2e;">⚡ <span style="color: #0891b2;">Photon</span><span style="color: #1a1a2e;">Path</span></span>
                        </td>
                    </tr>
                    
                    <!-- Main Card -->
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); padding: 40px 30px; text-align: center;">
                                        <div style="font-size: 42px; margin-bottom: 10px;">😢</div>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">Abonnement Annulé</h1>
                                        <p style="margin: 8px 0 0 0; font-size: 15px; color: rgba(255,255,255,0.9);">Vous passez au plan Spark gratuit</p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 35px 30px;">
                                        
                                        <p style="margin: 0 0 25px 0; font-size: 15px; color: #4a5568; line-height: 1.7;">
                                            Votre abonnement a été annulé. Vous êtes maintenant sur le plan <strong style="color: #10b981;">Spark (gratuit)</strong>.
                                        </p>
                                        
                                        <!-- What changes -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 20px 0;">
                                            <tr>
                                                <td style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 15px;">
                                                    <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #dc2626;">❌ Ce qui change</p>
                                                    <ul style="margin: 0; padding-left: 20px; color: #7f1d1d; font-size: 13px;">
                                                        <li>Limité à 100 requêtes/jour</li>
                                                        <li>10 simulations Monte Carlo/jour</li>
                                                    </ul>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- What you keep -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 20px 0;">
                                            <tr>
                                                <td style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 15px;">
                                                    <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #16a34a;">✅ Ce que vous gardez</p>
                                                    <ul style="margin: 0; padding-left: 20px; color: #166534; font-size: 13px;">
                                                        <li>Accès à l'API</li>
                                                        <li>Documentation complète</li>
                                                    </ul>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <p style="margin: 20px 0 0 0; font-size: 14px; color: #6b7280; text-align: center;">
                                            Vous pouvez réactiver votre abonnement à tout moment.
                                        </p>
                                        
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 30px;">
                            <p style="margin: 0; font-size: 13px; color: #6b7280;">© 2025 PhotonPath by BanasTechnologie</p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
    
</body>
</html>
"""
        
        return self.send_email(to_email, "😢 Abonnement annulé - PhotonPath", html)
    
    def send_payment_failed(self, to_email: str) -> bool:
        """📧 Email échec paiement."""
        
        html = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f4f7fa; line-height: 1.6;">
    
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f7fa;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                    
                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 25px;">
                            <span style="font-size: 26px; font-weight: 700; color: #1a1a2e;">⚡ <span style="color: #0891b2;">Photon</span><span style="color: #1a1a2e;">Path</span></span>
                        </td>
                    </tr>
                    
                    <!-- Main Card -->
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 40px 30px; text-align: center;">
                                        <div style="font-size: 42px; margin-bottom: 10px;">⚠️</div>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">Échec de Paiement</h1>
                                        <p style="margin: 8px 0 0 0; font-size: 15px; color: rgba(255,255,255,0.9);">Action requise</p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 35px 30px;">
                                        
                                        <p style="margin: 0 0 25px 0; font-size: 15px; color: #4a5568; line-height: 1.7;">
                                            Nous n'avons pas pu traiter votre dernier paiement. 
                                            <strong style="color: #dc2626;">Votre abonnement risque d'être suspendu.</strong>
                                        </p>
                                        
                                        <!-- Alert Box -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 20px 0;">
                                            <tr>
                                                <td style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 15px;">
                                                    <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #dc2626;">Raisons possibles :</p>
                                                    <ul style="margin: 0; padding-left: 20px; color: #7f1d1d; font-size: 13px;">
                                                        <li>Carte expirée ou invalide</li>
                                                        <li>Fonds insuffisants</li>
                                                        <li>Transaction bloquée par la banque</li>
                                                    </ul>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- CTA -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td align="center" style="padding: 20px 0;">
                                                    <a href="mailto:contact@banastechnologie.cloud" 
                                                       style="display: inline-block; padding: 14px 40px; background: linear-gradient(135deg, #ef4444, #dc2626); color: #ffffff; font-weight: 600; text-decoration: none; border-radius: 10px; font-size: 14px;">
                                                        📧 Nous Contacter
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 30px;">
                            <p style="margin: 0; font-size: 13px; color: #6b7280;">© 2025 PhotonPath by BanasTechnologie</p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
    
</body>
</html>
"""
        
        return self.send_email(to_email, "⚠️ Échec de paiement - Action requise - PhotonPath", html)


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
    print("📧 Test Email Service v3")
    print("=" * 50)
    
    service = init_email_service()
    
    if service.enabled:
        print(f"\n✅ Provider: {service.config.provider}")
        print(f"   From: {service.config.from_email}")
    else:
        print("\n⚠️ Email not configured")
        print("   Set RESEND_API_KEY or SMTP_* variables")