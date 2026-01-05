"""
PhotonPath Stripe Integration
==============================

Stripe payment integration for subscription management.
Uses TEST mode by default - switch to live keys for production.

Setup:
1. Create Stripe account at https://stripe.com
2. Get API keys from Dashboard > Developers > API keys
3. Set environment variables:
   - STRIPE_SECRET_KEY (sk_test_...)
   - STRIPE_WEBHOOK_SECRET (whsec_...)
   - STRIPE_PUBLISHABLE_KEY (pk_test_...)

Usage:
    from stripe_billing import StripeBilling
    
    billing = StripeBilling()
    
    # Create checkout session
    session = billing.create_checkout_session(
        price_id="price_xxx",
        customer_email="user@example.com",
        success_url="https://app.com/success",
        cancel_url="https://app.com/cancel"
    )

Author: PhotonPath
Version: 1.0.0
"""

import os
import secrets
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# Try to import stripe
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("⚠️ Stripe not installed. Run: pip install stripe")


class SubscriptionPlan(str, Enum):
    SPARK = "spark"        # Free
    PHOTON = "photon"      # 29€/mois
    BEAM = "beam"          # 99€/mois
    LASER = "laser"        # 299€/mois
    FUSION = "fusion"      # Sur devis


# Stripe Price IDs from environment variables
STRIPE_PRICES = {
    SubscriptionPlan.SPARK: None,  # Free plan, no Stripe price
    SubscriptionPlan.PHOTON: os.getenv("SUBSCRIPTION_PLAN_PHOTON"),
    SubscriptionPlan.BEAM: os.getenv("SUBSCRIPTION_PLAN_BEAM"),
    SubscriptionPlan.LASER: os.getenv("SUBSCRIPTION_PLAN_LASER"),
    SubscriptionPlan.FUSION: os.getenv("SUBSCRIPTION_PLAN_FUSION")
}

# Plan features for display
PLAN_FEATURES = {
    SubscriptionPlan.SPARK: {
        "name": "Spark",
        "emoji": "🔬",
        "tagline": "Découverte & étudiants",
        "price_monthly": 0,
        "price_yearly": 0,
        "requests_per_day": 100,
        "monte_carlo_per_day": 10,
        "batch_size": 5,
        "support": "Community",
        "features": [
            "100 requêtes API/jour",
            "10 simulations Monte Carlo/jour",
            "10 tissus de base",
            "Documentation complète",
            "Support communautaire"
        ],
        "limitations": [
            "Pas d'accès PDT Dosimetry",
            "Pas d'export CSV",
            "Pas de facture"
        ]
    },
    SubscriptionPlan.PHOTON: {
        "name": "Photon",
        "emoji": "💡",
        "tagline": "Doctorants & petits projets",
        "price_monthly": 29,
        "price_yearly": 290,
        "requests_per_day": 2000,
        "monte_carlo_per_day": 100,
        "batch_size": 20,
        "support": "Email",
        "features": [
            "2,000 requêtes API/jour",
            "100 simulations Monte Carlo/jour",
            "35 tissus complets",
            "PDT Dosimetry inclus",
            "Export CSV",
            "Support email",
            "Facture disponible",
            "-20% tarif académique"
        ],
        "limitations": []
    },
    SubscriptionPlan.BEAM: {
        "name": "Beam",
        "emoji": "🔦",
        "tagline": "Chercheurs académiques",
        "price_monthly": 99,
        "price_yearly": 990,
        "requests_per_day": 15000,
        "monte_carlo_per_day": 1000,
        "batch_size": 100,
        "support": "Email prioritaire",
        "features": [
            "15,000 requêtes API/jour",
            "1,000 simulations Monte Carlo/jour",
            "35 tissus complets",
            "Batch processing (100 items)",
            "API Analytics dashboard",
            "Support email prioritaire",
            "-30% tarif académique"
        ],
        "limitations": []
    },
    SubscriptionPlan.LASER: {
        "name": "Laser",
        "emoji": "⚡",
        "tagline": "Entreprises & startups",
        "price_monthly": 299,
        "price_yearly": 2990,
        "requests_per_day": 100000,
        "monte_carlo_per_day": 10000,
        "batch_size": 500,
        "support": "Dédié",
        "features": [
            "100,000 requêtes API/jour",
            "10,000 simulations Monte Carlo/jour",
            "Tissus custom uploadables",
            "Batch processing (500 items)",
            "API Analytics avancé",
            "Support dédié",
            "Intégration sur mesure",
            "-20% tarif académique"
        ],
        "limitations": []
    },
    SubscriptionPlan.FUSION: {
        "name": "Fusion",
        "emoji": "🌟",
        "tagline": "Pharma, hôpitaux, OEM",
        "price_monthly": None,  # Sur devis
        "price_yearly": None,
        "requests_per_day": 1000000,
        "monte_carlo_per_day": 100000,
        "batch_size": 1000,
        "support": "Dédié + SLA",
        "features": [
            "Requêtes illimitées",
            "Monte Carlo illimité + GPU",
            "Base de tissus custom illimitée",
            "Batch processing (1000+ items)",
            "Support dédié avec SLA",
            "Option déploiement on-premise",
            "Intégrations personnalisées",
            "Formation équipe incluse"
        ],
        "limitations": []
    }
}


@dataclass
class Customer:
    """Customer record."""
    id: str
    email: str
    stripe_customer_id: Optional[str] = None
    plan: SubscriptionPlan = SubscriptionPlan.SPARK
    api_key: str = field(default_factory=lambda: f"pk_{secrets.token_hex(24)}")
    created_at: datetime = field(default_factory=datetime.utcnow)
    subscription_id: Optional[str] = None
    subscription_status: str = "inactive"
    trial_end: Optional[datetime] = None


@dataclass
class CheckoutResult:
    """Checkout session result."""
    success: bool
    session_id: Optional[str] = None
    checkout_url: Optional[str] = None
    error: Optional[str] = None


# In-memory customer store (replace with database in production)
_customers: Dict[str, Customer] = {}
_api_keys: Dict[str, str] = {}  # api_key -> customer_id mapping


class StripeBilling:
    """
    Stripe billing integration.
    
    Parameters:
    -----------
    secret_key : str, optional
        Stripe secret key. Defaults to STRIPE_SECRET_KEY env var.
    webhook_secret : str, optional
        Stripe webhook secret. Defaults to STRIPE_WEBHOOK_SECRET env var.
    """
    
    def __init__(
        self,
        secret_key: str = None,
        webhook_secret: str = None
    ):
        self.secret_key = secret_key or os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")
        
        if STRIPE_AVAILABLE and self.secret_key:
            stripe.api_key = self.secret_key
            self._enabled = True
            
            # Check if using test keys
            if self.secret_key.startswith("sk_test_"):
                print("✅ Stripe initialized (TEST MODE)")
            elif self.secret_key.startswith("sk_live_"):
                print("✅ Stripe initialized (LIVE MODE)")
            else:
                print("⚠️ Invalid Stripe key format")
                self._enabled = False
        else:
            self._enabled = False
            if not STRIPE_AVAILABLE:
                print("⚠️ Stripe not available. Install with: pip install stripe")
            else:
                print("⚠️ Stripe not configured. Set STRIPE_SECRET_KEY env var.")
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def create_customer(self, email: str, name: str = None, send_welcome_email: bool = True) -> Customer:
        """Create a new customer."""
        customer_id = f"cust_{secrets.token_hex(12)}"
        api_key = f"pk_{secrets.token_hex(24)}"  # ← Générer AVANT d'utiliser
        
        # Create Stripe customer if enabled
        stripe_customer_id = None
        if self._enabled:
            try:
                stripe_customer = stripe.Customer.create(
                    email=email,
                    name=name,
                    metadata={
                        "photonpath_id": customer_id,
                        "plan": "spark",
                        "api_key": api_key,
                        "created_via": "photonpath_api"
                    }
                )
                stripe_customer_id = stripe_customer.id
                print(f"✅ Stripe customer created: {stripe_customer_id}")
            except Exception as e:
                print(f"⚠️ Failed to create Stripe customer: {e}")
        
        # Create local customer record
        customer = Customer(
            id=customer_id,
            email=email,
            stripe_customer_id=stripe_customer_id,
            plan=SubscriptionPlan.SPARK,
            api_key=api_key  # ← Utiliser la clé générée
        )
        
        # Store customer
        _customers[customer_id] = customer
        _api_keys[customer.api_key] = customer_id
        
        # Send welcome email
        if send_welcome_email:
            try:
                from email_service import get_email_service
                email_service = get_email_service()
                email_service.send_welcome_email(email, customer.api_key)
                print(f"✅ Welcome email sent to {email}")
            except Exception as e:
                print(f"⚠️ Welcome email failed: {e}")
        
        return customer
    
    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """Find customer by email."""
        for customer in _customers.values():
            if customer.email == email:
                return customer
        return None
    
    def get_customer_by_api_key(self, api_key: str) -> Optional[Customer]:
        """Find customer by API key."""
        customer_id = _api_keys.get(api_key)
        if customer_id:
            return _customers.get(customer_id)
        return None
    
    def create_checkout_session(
        self,
        customer_email: str,
        plan: SubscriptionPlan,
        success_url: str,
        cancel_url: str,
        trial_days: int = 14
    ) -> CheckoutResult:
        """
        Create Stripe Checkout session for subscription.
        
        Parameters:
        -----------
        customer_email : str
            Customer's email
        plan : SubscriptionPlan
            Plan to subscribe to
        success_url : str
            URL to redirect after successful payment
        cancel_url : str
            URL to redirect if cancelled
        trial_days : int
            Free trial period (default 14 days)
            
        Returns:
        --------
        CheckoutResult
        """
        if not self._enabled:
            return CheckoutResult(
                success=False,
                error="Stripe not configured"
            )
        
        if plan == SubscriptionPlan.SPARK:
            return CheckoutResult(
                success=False,
                error="Free plan doesn't require payment"
            )
        
        price_id = STRIPE_PRICES.get(plan)
        if not price_id:
            return CheckoutResult(
                success=False,
                error=f"No price configured for plan: {plan.value}"
            )
        
        try:
            # Get or create customer
            customer = self.get_customer_by_email(customer_email)
            if not customer:
                customer = self.create_customer(customer_email)
            
            # Create checkout session
            session_params = {
                "mode": "subscription",
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": price_id,
                    "quantity": 1
                }],
                "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": cancel_url,
                "customer_email": customer_email,
                "metadata": {
                    "photonpath_customer_id": customer.id,
                    "plan": plan.value
                },
                "subscription_data": {
                    "metadata": {
                        "photonpath_customer_id": customer.id,
                        "plan": plan.value
                    }
                }
            }
            
            # Add trial if specified
            if trial_days > 0:
                session_params["subscription_data"]["trial_period_days"] = trial_days
            
            # Use existing Stripe customer if available
            if customer.stripe_customer_id:
                session_params["customer"] = customer.stripe_customer_id
                del session_params["customer_email"]
            
            session = stripe.checkout.Session.create(**session_params)
            
            return CheckoutResult(
                success=True,
                session_id=session.id,
                checkout_url=session.url
            )
            
        except stripe.error.StripeError as e:
            return CheckoutResult(
                success=False,
                error=str(e)
            )
    
    def create_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Optional[str]:
        """
        Create Stripe Customer Portal session for subscription management.
        
        Returns portal URL or None if failed.
        """
        if not self._enabled:
            return None
        
        customer = _customers.get(customer_id)
        if not customer or not customer.stripe_customer_id:
            return None
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer.stripe_customer_id,
                return_url=return_url
            )
            return session.url
        except stripe.error.StripeError as e:
            print(f"⚠️ Portal session error: {e}")
            return None
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook events.
        
        Parameters:
        -----------
        payload : bytes
            Raw request body
        signature : str
            Stripe-Signature header
            
        Returns:
        --------
        dict : Event processing result
        """
        if not self._enabled or not self.webhook_secret:
            return {"success": False, "error": "Webhooks not configured"}
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
        except ValueError:
            return {"success": False, "error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            return {"success": False, "error": "Invalid signature"}
        
        # Handle event types
        event_type = event["type"]
        data = event["data"]["object"]
        
        if event_type == "checkout.session.completed":
            return self._handle_checkout_completed(data)
        
        elif event_type == "customer.subscription.updated":
            return self._handle_subscription_updated(data)
        
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(data)
        
        elif event_type == "invoice.payment_failed":
            return self._handle_payment_failed(data)
        
        return {"success": True, "event": event_type, "handled": False}
    
    def _handle_checkout_completed(self, session: Dict) -> Dict[str, Any]:
        """Handle successful checkout."""
        customer_id = session.get("metadata", {}).get("photonpath_customer_id")
        plan = session.get("metadata", {}).get("plan")
        subscription_id = session.get("subscription")
        
        if customer_id and customer_id in _customers:
            customer = _customers[customer_id]
            customer.subscription_id = subscription_id
            customer.subscription_status = "active"
            
            try:
                customer.plan = SubscriptionPlan(plan)
            except ValueError:
                pass
            
            # Regenerate API key for paid plans
            if customer.plan != SubscriptionPlan.SPARK:
                old_key = customer.api_key
                customer.api_key = f"sk_{secrets.token_hex(24)}"
                
                # Update API key mapping
                if old_key in _api_keys:
                    del _api_keys[old_key]
                _api_keys[customer.api_key] = customer_id
            
            # Send email notification
            try:
                from email_service import get_email_service
                email_service = get_email_service()
                email_service.send_subscription_activated(
                    customer.email, 
                    customer.plan.value, 
                    customer.api_key
                )
            except Exception as e:
                print(f"⚠️ Email notification failed: {e}")
            
            return {
                "success": True,
                "event": "checkout.session.completed",
                "customer_id": customer_id,
                "plan": plan,
                "api_key": customer.api_key
            }
        
        return {"success": False, "error": "Customer not found"}
    
    def _handle_subscription_updated(self, subscription: Dict) -> Dict[str, Any]:
        """Handle subscription update (upgrade/downgrade)."""
        customer_id = subscription.get("metadata", {}).get("photonpath_customer_id")
        status = subscription.get("status")
        
        if customer_id and customer_id in _customers:
            customer = _customers[customer_id]
            customer.subscription_status = status
            
            return {
                "success": True,
                "event": "customer.subscription.updated",
                "customer_id": customer_id,
                "status": status
            }
        
        return {"success": False, "error": "Customer not found"}
    
    def _handle_subscription_deleted(self, subscription: Dict) -> Dict[str, Any]:
        """Handle subscription cancellation."""
        customer_id = subscription.get("metadata", {}).get("photonpath_customer_id")
        
        if customer_id and customer_id in _customers:
            customer = _customers[customer_id]
            customer.plan = SubscriptionPlan.SPARK
            customer.subscription_status = "cancelled"
            customer.subscription_id = None
            
            # Downgrade API key
            old_key = customer.api_key
            customer.api_key = f"pk_{secrets.token_hex(24)}"
            
            if old_key in _api_keys:
                del _api_keys[old_key]
            _api_keys[customer.api_key] = customer_id
            
            # Send email notification
            try:
                from email_service import get_email_service
                email_service = get_email_service()
                email_service.send_subscription_cancelled(customer.email)
            except Exception as e:
                print(f"⚠️ Email notification failed: {e}")
            
            return {
                "success": True,
                "event": "customer.subscription.deleted",
                "customer_id": customer_id,
                "new_plan": "free"
            }
        
        return {"success": False, "error": "Customer not found"}
    
    def _handle_payment_failed(self, invoice: Dict) -> Dict[str, Any]:
        """Handle failed payment."""
        customer_email = invoice.get("customer_email")
        
        # Send email notification
        if customer_email:
            try:
                from email_service import get_email_service
                email_service = get_email_service()
                email_service.send_payment_failed(customer_email)
            except Exception as e:
                print(f"⚠️ Email notification failed: {e}")
        
        return {
            "success": True,
            "event": "invoice.payment_failed",
            "customer_email": customer_email
        }
    
    def get_plans(self) -> List[Dict[str, Any]]:
        """Get all available plans with features."""
        return [
            {
                "id": plan.value,
                **PLAN_FEATURES[plan]
            }
            for plan in SubscriptionPlan
        ]
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return customer info.
        
        Returns:
        --------
        dict or None : Customer info if valid, None if invalid
        """
        customer = self.get_customer_by_api_key(api_key)
        if not customer:
            return None
        
        return {
            "customer_id": customer.id,
            "email": customer.email,
            "plan": customer.plan.value,
            "subscription_status": customer.subscription_status,
            "limits": PLAN_FEATURES[customer.plan]
        }


# Global instance
_billing: Optional[StripeBilling] = None


def init_billing(secret_key: str = None, webhook_secret: str = None) -> StripeBilling:
    """Initialize global billing instance."""
    global _billing
    _billing = StripeBilling(secret_key, webhook_secret)
    return _billing


def get_billing() -> Optional[StripeBilling]:
    """Get global billing instance."""
    return _billing


# Demo customers (for testing without Stripe)
def create_demo_customers():
    """Create demo customers for testing."""
    demo_customers = [
        ("demo@photonpath.io", SubscriptionPlan.SPARK, "demo_key_12345"),
        ("photon@photonpath.io", SubscriptionPlan.PHOTON, "sk_photon_demo"),
        ("beam@photonpath.io", SubscriptionPlan.BEAM, "sk_beam_demo_key"),
        ("laser@photonpath.io", SubscriptionPlan.LASER, "sk_laser_demo_key"),
        ("fusion@photonpath.io", SubscriptionPlan.FUSION, "sk_fusion_demo_key"),
    ]
    
    for email, plan, api_key in demo_customers:
        customer = Customer(
            id=f"cust_{hashlib.md5(email.encode()).hexdigest()[:12]}",
            email=email,
            plan=plan,
            api_key=api_key,
            subscription_status="active" if plan != SubscriptionPlan.SPARK else "inactive"
        )
        _customers[customer.id] = customer
        _api_keys[api_key] = customer.id
    
    print(f"✅ Created {len(demo_customers)} demo customers")