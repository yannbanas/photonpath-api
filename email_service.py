"""
PhotonPath - Email Service
==========================

Module pour l'envoi d'emails via SMTP.
Supporte les notifications de paiement, bienvenue, etc.

Configuration .env:
    SMTP_HOST=ssl0.ovh.net
    SMTP_PORT=465
    SMTP_USER=contact@banastechnologie.cloud
    SMTP_PASSWORD=your_password
    SMTP_FROM_NAME=PhotonPath
    SMTP_FROM_EMAIL=contact@banastechnologie.cloud

Author: PhotonPath
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class SMTPConfig:
    """SMTP Configuration."""
    host: str
    port: int
    user: str
    password: str
    from_name: str
    from_email: str
    use_ssl: bool = True
    use_tls: bool = False


def get_smtp_config() -> Optional[SMTPConfig]:
    """Load SMTP configuration from environment."""
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    
    if not all([host, port, user, password]):
        print("⚠️ SMTP not configured (missing env vars)")
        return None
    
    return SMTPConfig(
        host=host,
        port=int(port),
        user=user,
        password=password,
        from_name=os.getenv("SMTP_FROM_NAME", "PhotonPath"),
        from_email=os.getenv("SMTP_FROM_EMAIL", user),
        use_ssl=int(port) == 465,
        use_tls=int(port) == 587
    )


# ============================================================================
# EMAIL SERVICE
# ============================================================================

class EmailService:
    """Service d'envoi d'emails."""
    
    def __init__(self, config: Optional[SMTPConfig] = None):
        self.config = config or get_smtp_config()
        self.enabled = self.config is not None
        
        if self.enabled:
            print(f"✅ Email service initialized ({self.config.host}:{self.config.port})")
        else:
            print("⚠️ Email service disabled (no SMTP config)")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Envoie un email.
        
        Args:
            to_email: Adresse du destinataire
            subject: Sujet de l'email
            html_content: Contenu HTML
            text_content: Contenu texte (optionnel, généré si absent)
            
        Returns:
            True si envoyé, False sinon
        """
        if not self.enabled:
            print(f"📧 [MOCK] Email to {to_email}: {subject}")
            return True
        
        try:
            # Créer le message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = to_email
            
            # Version texte
            if text_content is None:
                # Extraire le texte du HTML (basique)
                import re
                text_content = re.sub(r'<[^>]+>', '', html_content)
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Connexion et envoi
            if self.config.use_ssl:
                # Port 465 - SSL direct
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config.host, self.config.port, context=context) as server:
                    server.login(self.config.user, self.config.password)
                    server.sendmail(self.config.from_email, to_email, msg.as_string())
            else:
                # Port 587 - STARTTLS
                with smtplib.SMTP(self.config.host, self.config.port) as server:
                    server.starttls()
                    server.login(self.config.user, self.config.password)
                    server.sendmail(self.config.from_email, to_email, msg.as_string())
            
            print(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Email error: {e}")
            return False
    
    # ========================================================================
    # TEMPLATES D'EMAILS
    # ========================================================================
    
    def _get_email_header(self) -> str:
        """Header commun pour tous les emails."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PhotonPath</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f7fa; line-height: 1.6;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f7fa;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                            
                            <!-- Logo Header -->
                            <tr>
                                <td align="center" style="padding-bottom: 30px;">
                                    <table role="presentation" cellspacing="0" cellpadding="0">
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #00d4aa 0%, #7c3aed 100%); width: 50px; height: 50px; border-radius: 12px; text-align: center; vertical-align: middle;">
                                                <span style="font-size: 24px;">⚡</span>
                                            </td>
                                            <td style="padding-left: 15px;">
                                                <span style="font-size: 28px; font-weight: 700; color: #1a1a2e; letter-spacing: -0.5px;">PhotonPath</span>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Main Content Card -->
                            <tr>
                                <td>
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08); overflow: hidden;">
        """
    
    def _get_email_footer(self) -> str:
        """Footer commun pour tous les emails."""
        return """
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td align="center" style="padding-top: 30px;">
                                    <p style="margin: 0; font-size: 13px; color: #8896a6;">
                                        © 2025 PhotonPath by BanasTechnologie
                                    </p>
                                    <p style="margin: 8px 0 0 0; font-size: 12px; color: #a0aec0;">
                                        API Biophotonique pour la Recherche
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
        """Email de bienvenue avec la clé API."""
        subject = "🚀 Bienvenue sur PhotonPath - Votre clé API"
        
        html = self._get_email_header() + f"""
                                        <!-- Banner -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #00d4aa 0%, #7c3aed 50%, #ec4899 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #ffffff; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                                    🎉 Bienvenue !
                                                </h1>
                                                <p style="margin: 10px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">
                                                    Votre compte PhotonPath est prêt
                                                </p>
                                            </td>
                                        </tr>
                                        
                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Merci de rejoindre PhotonPath ! Votre compte est maintenant <strong style="color: #00d4aa;">actif</strong> et prêt à utiliser.
                                                </p>
                                                
                                                <!-- API Key Box -->
                                                <div style="background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border: 2px solid #00d4aa; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                    <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #059669; text-transform: uppercase; letter-spacing: 1px;">
                                                        🔑 Votre Clé API
                                                    </p>
                                                    <p style="margin: 0; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 14px; color: #065f46; background-color: #ffffff; padding: 15px; border-radius: 8px; word-break: break-all; border: 1px solid #a7f3d0;">
                                                        {api_key}
                                                    </p>
                                                    <p style="margin: 12px 0 0 0; font-size: 12px; color: #6b7280;">
                                                        ⚠️ Gardez cette clé secrète ! Ne la partagez jamais publiquement.
                                                    </p>
                                                </div>
                                                
                                                <!-- Quick Start -->
                                                <div style="background-color: #f8fafc; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                    <p style="margin: 0 0 15px 0; font-size: 14px; font-weight: 600; color: #1e293b;">
                                                        ⚡ Démarrage rapide
                                                    </p>
                                                    <pre style="margin: 0; font-family: 'SF Mono', 'Courier New', monospace; font-size: 13px; color: #e2e8f0; background-color: #1e293b; padding: 15px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap;"><span style="color: #94a3b8;"># Python</span>
<span style="color: #f472b6;">import</span> <span style="color: #7dd3fc;">requests</span>

response = requests.get(
    <span style="color: #a5f3fc;">"https://photonpath-api.up.railway.app/v2/tissues"</span>,
    headers=<span style="color: #fcd34d;">{{"X-API-Key": "VOTRE_CLE_API"}}</span>
)</pre>
                                                </div>
                                                
                                                <!-- CTA Button -->
                                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                    <tr>
                                                        <td align="center" style="padding: 20px 0;">
                                                            <a href="https://photonpath-api-production.up.railway.app/docs" 
                                                               style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #00d4aa 0%, #7c3aed 100%); color: #ffffff; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 10px; box-shadow: 0 4px 14px rgba(0, 212, 170, 0.4);">
                                                                📖 Voir la Documentation
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                                
                                                <!-- Plan Info -->
                                                <div style="border-top: 1px solid #e2e8f0; padding-top: 25px; margin-top: 25px;">
                                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td width="50%" style="padding: 10px 0;">
                                                                <p style="margin: 0; font-size: 12px; color: #94a3b8; text-transform: uppercase;">Plan actuel</p>
                                                                <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: 600; color: #1e293b;">🔬 Spark (Gratuit)</p>
                                                            </td>
                                                            <td width="50%" style="padding: 10px 0;">
                                                                <p style="margin: 0; font-size: 12px; color: #94a3b8; text-transform: uppercase;">Limites</p>
                                                                <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: 600; color: #1e293b;">100 req/jour</p>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </div>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)
    
    def send_subscription_activated(self, to_email: str, plan: str, api_key: str) -> bool:
        """Email de confirmation d'abonnement."""
        plan_info = {
            "spark": {"name": "Spark", "emoji": "🔬", "price": "Gratuit", "limit": "100 req/jour"},
            "photon": {"name": "Photon", "emoji": "💡", "price": "29€/mois", "limit": "2,000 req/jour"},
            "beam": {"name": "Beam", "emoji": "🔦", "price": "99€/mois", "limit": "15,000 req/jour"},
            "laser": {"name": "Laser", "emoji": "⚡", "price": "299€/mois", "limit": "100,000 req/jour"},
            "fusion": {"name": "Fusion", "emoji": "🌟", "price": "Sur devis", "limit": "Illimité"}
        }
        info = plan_info.get(plan, plan_info["spark"])
        
        subject = f"✅ Abonnement {info['name']} activé - PhotonPath"
        
        html = self._get_email_header() + f"""
                                        <!-- Banner -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: #ffffff;">
                                                    ✅ Abonnement Activé !
                                                </h1>
                                                <p style="margin: 10px 0 0 0; font-size: 18px; color: rgba(255,255,255,0.9);">
                                                    {info['emoji']} Plan {info['name']}
                                                </p>
                                            </td>
                                        </tr>
                                        
                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Félicitations ! Votre abonnement <strong style="color: #059669;">{info['name']}</strong> est maintenant actif.
                                                </p>
                                                
                                                <!-- Plan Summary -->
                                                <div style="background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); border-radius: 12px; padding: 25px; margin: 25px 0; border: 1px solid #a7f3d0;">
                                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                        <tr>
                                                            <td style="padding: 8px 0; border-bottom: 1px solid #d1fae5;">
                                                                <span style="color: #6b7280; font-size: 14px;">Plan</span>
                                                            </td>
                                                            <td style="padding: 8px 0; border-bottom: 1px solid #d1fae5; text-align: right;">
                                                                <span style="color: #065f46; font-size: 16px; font-weight: 600;">{info['emoji']} {info['name']}</span>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 8px 0; border-bottom: 1px solid #d1fae5;">
                                                                <span style="color: #6b7280; font-size: 14px;">Prix</span>
                                                            </td>
                                                            <td style="padding: 8px 0; border-bottom: 1px solid #d1fae5; text-align: right;">
                                                                <span style="color: #065f46; font-size: 16px; font-weight: 600;">{info['price']}</span>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 8px 0;">
                                                                <span style="color: #6b7280; font-size: 14px;">Limite</span>
                                                            </td>
                                                            <td style="padding: 8px 0; text-align: right;">
                                                                <span style="color: #065f46; font-size: 16px; font-weight: 600;">{info['limit']}</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </div>
                                                
                                                <!-- New API Key -->
                                                <div style="background-color: #fef3c7; border: 2px solid #f59e0b; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                    <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600; color: #b45309; text-transform: uppercase; letter-spacing: 1px;">
                                                        🔑 Nouvelle Clé API
                                                    </p>
                                                    <p style="margin: 0; font-family: 'SF Mono', monospace; font-size: 14px; color: #92400e; background-color: #ffffff; padding: 15px; border-radius: 8px; word-break: break-all; border: 1px solid #fcd34d;">
                                                        {api_key}
                                                    </p>
                                                    <p style="margin: 12px 0 0 0; font-size: 12px; color: #92400e;">
                                                        ⚠️ Cette clé remplace votre ancienne clé. Mettez à jour vos applications.
                                                    </p>
                                                </div>
                                                
                                                <!-- CTA -->
                                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                    <tr>
                                                        <td align="center" style="padding: 20px 0;">
                                                            <a href="https://photonpath-api-production.up.railway.app/docs" 
                                                               style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 10px; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);">
                                                                🚀 Commencer à utiliser l'API
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)
    
    def send_subscription_cancelled(self, to_email: str) -> bool:
        """Email de confirmation d'annulation."""
        subject = "😢 Votre abonnement PhotonPath a été annulé"
        
        html = self._get_email_header() + """
                                        <!-- Banner -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">
                                                    Abonnement Annulé
                                                </h1>
                                                <p style="margin: 10px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.8);">
                                                    Nous sommes tristes de vous voir partir
                                                </p>
                                            </td>
                                        </tr>
                                        
                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Votre abonnement PhotonPath a été annulé. Votre compte a été rétrogradé au plan <strong>Spark (gratuit)</strong>.
                                                </p>
                                                
                                                <!-- What changes -->
                                                <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                    <p style="margin: 0 0 15px 0; font-size: 14px; font-weight: 600; color: #991b1b;">
                                                        Ce qui change :
                                                    </p>
                                                    <ul style="margin: 0; padding-left: 20px; color: #7f1d1d;">
                                                        <li style="margin-bottom: 8px;">Limite réduite à 100 requêtes/jour</li>
                                                        <li style="margin-bottom: 8px;">10 simulations Monte Carlo/jour</li>
                                                        <li style="margin-bottom: 8px;">Nouvelle clé API générée</li>
                                                    </ul>
                                                </div>
                                                
                                                <!-- What stays -->
                                                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                    <p style="margin: 0 0 15px 0; font-size: 14px; font-weight: 600; color: #166534;">
                                                        Ce que vous gardez :
                                                    </p>
                                                    <ul style="margin: 0; padding-left: 20px; color: #15803d;">
                                                        <li style="margin-bottom: 8px;">Accès à l'API</li>
                                                        <li style="margin-bottom: 8px;">Documentation complète</li>
                                                        <li style="margin-bottom: 8px;">Support communautaire</li>
                                                    </ul>
                                                </div>
                                                
                                                <p style="margin: 25px 0; font-size: 16px; color: #4a5568; text-align: center;">
                                                    Vous pouvez réactiver votre abonnement à tout moment.
                                                </p>
                                                
                                                <!-- CTA -->
                                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                    <tr>
                                                        <td align="center" style="padding: 20px 0;">
                                                            <a href="mailto:contact@banastechnologie.cloud" 
                                                               style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #00d4aa 0%, #7c3aed 100%); color: #ffffff; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 10px;">
                                                                💬 Nous donner votre feedback
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)
    
    def send_payment_failed(self, to_email: str) -> bool:
        """Email d'échec de paiement."""
        subject = "⚠️ Échec de paiement - Action requise"
        
        html = self._get_email_header() + """
                                        <!-- Banner -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff;">
                                                    ⚠️ Échec de Paiement
                                                </h1>
                                                <p style="margin: 10px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">
                                                    Action requise pour maintenir votre accès
                                                </p>
                                            </td>
                                        </tr>
                                        
                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="margin: 0 0 25px 0; font-size: 16px; color: #4a5568;">
                                                    Nous n'avons pas pu traiter votre paiement pour l'abonnement PhotonPath.
                                                </p>
                                                
                                                <!-- Alert Box -->
                                                <div style="background-color: #fef2f2; border: 2px solid #ef4444; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                    <p style="margin: 0 0 15px 0; font-size: 14px; font-weight: 600; color: #991b1b;">
                                                        🚨 Que se passe-t-il ?
                                                    </p>
                                                    <ul style="margin: 0; padding-left: 20px; color: #7f1d1d;">
                                                        <li style="margin-bottom: 8px;">Votre carte a été refusée ou a expiré</li>
                                                        <li style="margin-bottom: 8px;">Votre accès risque d'être suspendu</li>
                                                        <li style="margin-bottom: 8px;">Mettez à jour vos infos de paiement</li>
                                                    </ul>
                                                </div>
                                                
                                                <!-- CTA -->
                                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                    <tr>
                                                        <td align="center" style="padding: 20px 0;">
                                                            <a href="mailto:contact@banastechnologie.cloud" 
                                                               style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: #ffffff; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 10px; box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);">
                                                                📧 Nous Contacter
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                                
                                                <p style="margin: 25px 0 0 0; font-size: 14px; color: #6b7280; text-align: center;">
                                                    Si vous pensez qu'il s'agit d'une erreur, contactez-nous à<br>
                                                    <a href="mailto:contact@banastechnologie.cloud" style="color: #7c3aed;">contact@banastechnologie.cloud</a>
                                                </p>
                                            </td>
                                        </tr>
        """ + self._get_email_footer()
        
        return self.send_email(to_email, subject, html)


# ============================================================================
# SINGLETON
# ============================================================================

_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def init_email_service() -> EmailService:
    """Initialize email service."""
    global _email_service
    _email_service = EmailService()
    return _email_service


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("="*60)
    print("📧 Test Email Service")
    print("="*60)
    
    service = init_email_service()
    
    if service.enabled:
        print(f"\n✅ SMTP configuré: {service.config.host}:{service.config.port}")
        print(f"   From: {service.config.from_name} <{service.config.from_email}>")
        
        # Test d'envoi (décommenter pour tester)
        #test_email = "xxx@gmail.com"
        #service.send_welcome_email(test_email, "pk_test_12345")
        
        print("\n💡 Pour tester, décommente les lignes dans le __main__")
    else:
        print("\n⚠️ SMTP non configuré")
        print("   Ajoute ces variables dans .env:")
        print("   SMTP_HOST=ssl0.ovh.net")
        print("   SMTP_PORT=465")
        print("   SMTP_USER=xxx@banastechnologie.cloud")
        print("   SMTP_PASSWORD=your_password")