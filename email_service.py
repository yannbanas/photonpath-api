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
    # PROFESSIONAL EMAIL TEMPLATES
    # ========================================================================
    
    def _base_template(self, header_gradient: str, header_emoji: str, header_title: str, header_subtitle: str, body_content: str) -> str:
        """Template de base professionnel."""
        return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{header_title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0a0a0f; line-height: 1.6;">
    
    <!-- Wrapper -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0f;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                
                <!-- Container -->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                    
                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding-bottom: 30px;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #00ffc8 0%, #7c3aed 50%, #00d4ff 100%); -webkit-background-clip: text; background-clip: text;">
                                        <span style="font-size: 32px; font-weight: 800; color: #00ffc8; letter-spacing: -1px;">⚡ PhotonPath</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Main Card -->
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: linear-gradient(145deg, #12121a 0%, #1a1a2e 100%); border-radius: 24px; overflow: hidden; border: 1px solid rgba(124, 58, 237, 0.3); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 100px rgba(124, 58, 237, 0.1);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="background: {header_gradient}; padding: 50px 40px; text-align: center; position: relative;">
                                        <div style="font-size: 56px; margin-bottom: 15px;">{header_emoji}</div>
                                        <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #ffffff; text-shadow: 0 2px 10px rgba(0,0,0,0.3);">{header_title}</h1>
                                        <p style="margin: 12px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.85); font-weight: 400;">{header_subtitle}</p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 45px 40px;">
                                        {body_content}
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding-top: 35px;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding: 0 15px;">
                                        <a href="https://photonpath-api-production.up.railway.app/docs" style="color: #8896a6; font-size: 13px; text-decoration: none;">Documentation</a>
                                    </td>
                                    <td style="color: #3a3a4a;">|</td>
                                    <td style="padding: 0 15px;">
                                        <a href="mailto:contact@banastechnologie.cloud" style="color: #8896a6; font-size: 13px; text-decoration: none;">Support</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin: 20px 0 0 0; font-size: 12px; color: #4a4a5a;">
                                © 2025 PhotonPath by BanasTechnologie<br>
                                <span style="color: #3a3a4a;">Plateforme de simulation biophotonique</span>
                            </p>
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
        """📧 Email de bienvenue avec clé API."""
        
        body_content = f"""
        <p style="margin: 0 0 25px 0; font-size: 17px; color: #c8c8d0; line-height: 1.7;">
            Merci de rejoindre <strong style="color: #00ffc8;">PhotonPath</strong> ! Votre compte est maintenant 
            <span style="background: linear-gradient(90deg, #00ffc8, #00d4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 600;">actif</span> 
            et prêt à être utilisé.
        </p>
        
        <!-- API Key Box -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 30px 0;">
            <tr>
                <td style="background: linear-gradient(135deg, rgba(0, 255, 200, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%); border: 2px solid #00ffc8; border-radius: 16px; padding: 25px;">
                    <p style="margin: 0 0 12px 0; font-size: 11px; font-weight: 700; color: #00ffc8; text-transform: uppercase; letter-spacing: 2px;">
                        🔑 Votre Clé API
                    </p>
                    <p style="margin: 0; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 14px; color: #ffffff; background: rgba(0, 0, 0, 0.4); padding: 16px; border-radius: 10px; word-break: break-all; border: 1px solid rgba(0, 255, 200, 0.2);">
                        {api_key}
                    </p>
                    <p style="margin: 15px 0 0 0; font-size: 12px; color: #ff6b6b;">
                        ⚠️ Conservez cette clé en lieu sûr — ne la partagez jamais !
                    </p>
                </td>
            </tr>
        </table>
        
        <!-- Plan Info -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
            <tr>
                <td style="background: rgba(255, 255, 255, 0.03); border-radius: 12px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.05);">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                        <tr>
                            <td width="50%" style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <span style="color: #6b6b7a; font-size: 13px;">Plan</span>
                            </td>
                            <td width="50%" style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: right;">
                                <span style="color: #00ffc8; font-weight: 600; font-size: 14px;">🔬 Spark (Gratuit)</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <span style="color: #6b6b7a; font-size: 13px;">Requêtes/jour</span>
                            </td>
                            <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: right;">
                                <span style="color: #ffffff; font-weight: 500; font-size: 14px;">100</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;">
                                <span style="color: #6b6b7a; font-size: 13px;">Monte Carlo/jour</span>
                            </td>
                            <td style="padding: 8px 0; text-align: right;">
                                <span style="color: #ffffff; font-weight: 500; font-size: 14px;">10</span>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        
        <!-- Quick Start -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
            <tr>
                <td style="background: #0d1117; border-radius: 12px; padding: 20px; border: 1px solid #30363d;">
                    <p style="margin: 0 0 12px 0; font-size: 13px; font-weight: 600; color: #c9d1d9;">
                        ⚡ Quick Start
                    </p>
                    <code style="display: block; font-family: 'SF Mono', monospace; font-size: 12px; color: #7ee787; line-height: 1.8;">
                        <span style="color: #ff7b72;">curl</span> <span style="color: #a5d6ff;">-H</span> <span style="color: #a5d6ff;">"X-API-Key: {api_key[:20]}..."</span> \\<br>
                        &nbsp;&nbsp;<span style="color: #79c0ff;">https://photonpath-api-production.up.railway.app/v2/tissues</span>
                    </code>
                </td>
            </tr>
        </table>
        
        <!-- CTA Button -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td align="center" style="padding: 25px 0 10px 0;">
                    <a href="https://photonpath-api-production.up.railway.app/docs" 
                       style="display: inline-block; padding: 16px 45px; background: linear-gradient(135deg, #00ffc8 0%, #7c3aed 50%, #00d4ff 100%); color: #0a0a0f; font-weight: 700; text-decoration: none; border-radius: 12px; font-size: 15px; box-shadow: 0 10px 30px rgba(0, 255, 200, 0.3); text-transform: uppercase; letter-spacing: 1px;">
                        📖 Explorer la Documentation
                    </a>
                </td>
            </tr>
        </table>
        """
        
        html = self._base_template(
            header_gradient="linear-gradient(135deg, #00ffc8 0%, #00d4aa 30%, #7c3aed 70%, #6366f1 100%)",
            header_emoji="🎉",
            header_title="Bienvenue !",
            header_subtitle="Votre compte PhotonPath est prêt",
            body_content=body_content
        )
        
        return self.send_email(to_email, "🚀 Bienvenue sur PhotonPath - Votre clé API", html)
    
    def send_subscription_activated(self, to_email: str, plan: str, api_key: str) -> bool:
        """📧 Email confirmation abonnement."""
        
        plan_info = {
            "spark": {"name": "Spark", "emoji": "🔬", "price": "Gratuit", "color": "#00ffc8"},
            "photon": {"name": "Photon", "emoji": "💡", "price": "29€/mois", "color": "#fbbf24"},
            "beam": {"name": "Beam", "emoji": "🔦", "price": "99€/mois", "color": "#f97316"},
            "laser": {"name": "Laser", "emoji": "⚡", "price": "299€/mois", "color": "#ef4444"},
            "fusion": {"name": "Fusion", "emoji": "🌟", "price": "Sur devis", "color": "#a855f7"}
        }
        info = plan_info.get(plan, plan_info["spark"])
        
        body_content = f"""
        <p style="margin: 0 0 25px 0; font-size: 17px; color: #c8c8d0; line-height: 1.7;">
            Votre abonnement <strong style="color: {info['color']};">{info['name']}</strong> est maintenant actif !
            Profitez de toutes les fonctionnalités de votre nouveau plan.
        </p>
        
        <!-- Plan Summary -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
            <tr>
                <td style="background: rgba(255, 255, 255, 0.03); border-radius: 12px; padding: 20px; border: 1px solid {info['color']}40;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                        <tr>
                            <td style="padding: 8px 0; text-align: center;">
                                <span style="font-size: 48px;">{info['emoji']}</span>
                                <p style="margin: 10px 0 5px 0; font-size: 24px; font-weight: 700; color: {info['color']};">Plan {info['name']}</p>
                                <p style="margin: 0; font-size: 16px; color: #6b6b7a;">{info['price']}</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        
        <!-- New API Key -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 30px 0;">
            <tr>
                <td style="background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.1) 100%); border: 2px solid #fbbf24; border-radius: 16px; padding: 25px;">
                    <p style="margin: 0 0 12px 0; font-size: 11px; font-weight: 700; color: #fbbf24; text-transform: uppercase; letter-spacing: 2px;">
                        🔑 Nouvelle Clé API
                    </p>
                    <p style="margin: 0; font-family: 'SF Mono', monospace; font-size: 14px; color: #ffffff; background: rgba(0, 0, 0, 0.4); padding: 16px; border-radius: 10px; word-break: break-all; border: 1px solid rgba(251, 191, 36, 0.2);">
                        {api_key}
                    </p>
                    <p style="margin: 15px 0 0 0; font-size: 12px; color: #ff6b6b;">
                        ⚠️ Cette clé remplace votre ancienne clé !
                    </p>
                </td>
            </tr>
        </table>
        
        <!-- CTA -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td align="center" style="padding: 25px 0 10px 0;">
                    <a href="https://photonpath-api-production.up.railway.app/docs" 
                       style="display: inline-block; padding: 16px 45px; background: linear-gradient(135deg, {info['color']}, #7c3aed); color: #ffffff; font-weight: 700; text-decoration: none; border-radius: 12px; font-size: 15px; box-shadow: 0 10px 30px rgba(124, 58, 237, 0.3);">
                        🚀 Commencer à utiliser l'API
                    </a>
                </td>
            </tr>
        </table>
        """
        
        html = self._base_template(
            header_gradient="linear-gradient(135deg, #10b981 0%, #059669 50%, #047857 100%)",
            header_emoji="✅",
            header_title="Abonnement Activé !",
            header_subtitle=f"Plan {info['name']} - {info['price']}",
            body_content=body_content
        )
        
        return self.send_email(to_email, f"✅ Abonnement {info['name']} activé - PhotonPath", html)
    
    def send_subscription_cancelled(self, to_email: str) -> bool:
        """📧 Email annulation."""
        
        body_content = """
        <p style="margin: 0 0 25px 0; font-size: 17px; color: #c8c8d0; line-height: 1.7;">
            Votre abonnement a été annulé. Vous êtes maintenant sur le plan 
            <strong style="color: #00ffc8;">Spark (gratuit)</strong>.
        </p>
        
        <!-- What changes -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
            <tr>
                <td style="background: rgba(239, 68, 68, 0.1); border-radius: 12px; padding: 20px; border: 1px solid rgba(239, 68, 68, 0.3);">
                    <p style="margin: 0 0 10px 0; font-size: 14px; font-weight: 600; color: #ef4444;">
                        ❌ Ce qui change
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #c8c8d0; font-size: 14px;">
                        <li>Limité à 100 requêtes/jour</li>
                        <li>10 simulations Monte Carlo/jour</li>
                        <li>Accès aux fonctionnalités de base uniquement</li>
                    </ul>
                </td>
            </tr>
        </table>
        
        <!-- What you keep -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
            <tr>
                <td style="background: rgba(0, 255, 200, 0.1); border-radius: 12px; padding: 20px; border: 1px solid rgba(0, 255, 200, 0.3);">
                    <p style="margin: 0 0 10px 0; font-size: 14px; font-weight: 600; color: #00ffc8;">
                        ✅ Ce que vous gardez
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #c8c8d0; font-size: 14px;">
                        <li>Accès à l'API avec votre clé existante</li>
                        <li>Documentation complète</li>
                        <li>Support communautaire</li>
                    </ul>
                </td>
            </tr>
        </table>
        
        <p style="margin: 25px 0 0 0; font-size: 15px; color: #8896a6; text-align: center;">
            Vous pouvez réactiver votre abonnement à tout moment.
        </p>
        """
        
        html = self._base_template(
            header_gradient="linear-gradient(135deg, #6b7280 0%, #4b5563 100%)",
            header_emoji="😢",
            header_title="Abonnement Annulé",
            header_subtitle="Vous passez au plan Spark gratuit",
            body_content=body_content
        )
        
        return self.send_email(to_email, "😢 Abonnement annulé - PhotonPath", html)
    
    def send_payment_failed(self, to_email: str) -> bool:
        """📧 Email échec paiement."""
        
        body_content = """
        <p style="margin: 0 0 25px 0; font-size: 17px; color: #c8c8d0; line-height: 1.7;">
            Nous n'avons pas pu traiter votre dernier paiement. 
            <strong style="color: #ef4444;">Votre abonnement risque d'être suspendu.</strong>
        </p>
        
        <!-- Alert Box -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 25px 0;">
            <tr>
                <td style="background: rgba(239, 68, 68, 0.15); border-radius: 12px; padding: 25px; border: 1px solid rgba(239, 68, 68, 0.4);">
                    <p style="margin: 0 0 15px 0; font-size: 15px; font-weight: 600; color: #ef4444;">
                        ⚠️ Raisons possibles
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #c8c8d0; font-size: 14px; line-height: 1.8;">
                        <li>Carte expirée ou invalide</li>
                        <li>Fonds insuffisants</li>
                        <li>Transaction bloquée par votre banque</li>
                    </ul>
                </td>
            </tr>
        </table>
        
        <!-- CTA -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr>
                <td align="center" style="padding: 25px 0 10px 0;">
                    <a href="mailto:contact@banastechnologie.cloud" 
                       style="display: inline-block; padding: 16px 45px; background: linear-gradient(135deg, #ef4444, #dc2626); color: #ffffff; font-weight: 700; text-decoration: none; border-radius: 12px; font-size: 15px; box-shadow: 0 10px 30px rgba(239, 68, 68, 0.3);">
                        📧 Nous Contacter
                    </a>
                </td>
            </tr>
        </table>
        
        <p style="margin: 25px 0 0 0; font-size: 13px; color: #6b6b7a; text-align: center;">
            Si vous avez des questions, contactez-nous à<br>
            <a href="mailto:contact@banastechnologie.cloud" style="color: #00ffc8;">contact@banastechnologie.cloud</a>
        </p>
        """
        
        html = self._base_template(
            header_gradient="linear-gradient(135deg, #ef4444 0%, #dc2626 50%, #b91c1c 100%)",
            header_emoji="⚠️",
            header_title="Échec de Paiement",
            header_subtitle="Action requise pour maintenir votre accès",
            body_content=body_content
        )
        
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
        
        # Uncomment to test:
        # result = service.send_welcome_email("test@example.com", "pk_test_123456789")
        # print(f"   Test: {'✅ Sent' if result else '❌ Failed'}")
    else:
        print("\n⚠️ Email not configured")
        print("   Set RESEND_API_KEY or SMTP_* variables")