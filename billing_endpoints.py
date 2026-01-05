"""
PhotonPath Billing & Rate Limiting API Endpoints
=================================================

Add these endpoints to api_v2.py or import as a router.

Usage:
    from billing_endpoints import billing_router
    app.include_router(billing_router)

Author: PhotonPath
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import os

from rate_limiter import (
    RateLimiter, 
    init_rate_limiter, 
    get_rate_limiter,
    Plan,
    PLAN_LIMITS
)
from stripe_billing import (
    StripeBilling,
    init_billing,
    get_billing,
    create_demo_customers,
    SubscriptionPlan,
    PLAN_FEATURES
)


# ============================================================================
# ROUTER
# ============================================================================

billing_router = APIRouter(prefix="/billing", tags=["Billing"])
usage_router = APIRouter(prefix="/usage", tags=["Usage & Limits"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CheckoutRequest(BaseModel):
    email: EmailStr
    plan: str  # "research", "pro", "enterprise"
    success_url: str
    cancel_url: str
    trial_days: int = 14


class CustomerCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_billing_system(
    redis_url: str = None,
    stripe_secret_key: str = None,
    stripe_webhook_secret: str = None
):
    """
    Initialize billing and rate limiting systems.
    
    Call this at API startup.
    """
    # Initialize Redis rate limiter
    redis_url = redis_url or os.getenv("REDIS_URL")
    init_rate_limiter(redis_url)
    
    # Initialize Stripe billing
    stripe_key = stripe_secret_key or os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = stripe_webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET")
    init_billing(stripe_key, webhook_secret)
    
    # Create demo customers for testing
    create_demo_customers()
    
    limiter = get_rate_limiter()
    billing = get_billing()
    
    print("=" * 50)
    print("📊 Billing System Status:")
    print(f"   Redis: {'✅ Connected' if limiter and limiter.is_redis else '⚠️ In-memory fallback'}")
    print(f"   Stripe: {'✅ Enabled' if billing and billing.is_enabled else '⚠️ Disabled'}")
    print("=" * 50)


# ============================================================================
# RATE LIMITING DEPENDENCY
# ============================================================================

async def rate_limit_check(
    x_api_key: str = Header(None),
    request: Request = None
):
    """
    FastAPI dependency for rate limiting.
    
    Add to endpoints: user = Depends(rate_limit_check)
    """
    limiter = get_rate_limiter()
    billing = get_billing()
    
    if not limiter:
        # No rate limiting configured
        return {"user": "anonymous", "plan": "spark", "limited": False}
    
    # Get API key
    api_key = x_api_key or "anonymous"
    
    # Get customer plan
    plan = Plan.SPARK
    if billing and api_key != "anonymous":
        customer_info = billing.validate_api_key(api_key)
        if customer_info:
            try:
                plan = Plan(customer_info["plan"])
            except ValueError:
                plan = Plan.SPARK
    
    # Check rate limit
    endpoint_type = "general"
    if request and "monte" in request.url.path.lower():
        endpoint_type = "monte_carlo"
    
    result = limiter.check_rate_limit(api_key, plan, endpoint_type)
    
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": result.limit,
                "remaining": result.remaining,
                "reset_at": result.reset_at.isoformat(),
                "retry_after": result.retry_after
            },
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": result.reset_at.isoformat(),
                "Retry-After": str(result.retry_after or 60)
            }
        )
    
    return {
        "user": api_key[:12] + "..." if len(api_key) > 12 else api_key,
        "plan": plan.value,
        "remaining": result.remaining,
        "limited": False
    }


# ============================================================================
# USAGE ENDPOINTS
# ============================================================================

@usage_router.get("/limits")
async def get_usage_limits(x_api_key: str = Header(None)):
    """
    Get current usage and remaining limits for your API key.
    
    Returns:
    - Daily usage/limits
    - Per-minute usage/limits
    - Monte Carlo usage/limits
    - Current plan
    """
    limiter = get_rate_limiter()
    billing = get_billing()
    
    if not limiter:
        return {
            "message": "Rate limiting not configured",
            "plan": "unlimited"
        }
    
    api_key = x_api_key or "anonymous"
    
    # Get plan
    plan = Plan.SPARK
    if billing and api_key != "anonymous":
        customer_info = billing.validate_api_key(api_key)
        if customer_info:
            try:
                plan = Plan(customer_info["plan"])
            except ValueError:
                plan = Plan.SPARK
    
    usage = limiter.get_usage(api_key, plan)
    
    return {
        "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
        "plan": plan.value,
        "usage": usage
    }


@usage_router.get("/plans")
async def get_available_plans():
    """
    Get all available subscription plans with features and pricing.
    """
    return {
        "plans": [
            {
                "id": plan.value,
                **PLAN_FEATURES[plan]
            }
            for plan in SubscriptionPlan
        ]
    }


# ============================================================================
# BILLING ENDPOINTS
# ============================================================================

@billing_router.post("/customers")
async def create_customer(data: CustomerCreate):
    """
    Create a new customer account.
    
    Returns API key for the free plan.
    """
    billing = get_billing()
    
    if not billing:
        raise HTTPException(503, "Billing not configured")
    
    # Check if customer exists
    existing = billing.get_customer_by_email(data.email)
    if existing:
        return {
            "message": "Customer already exists",
            "customer_id": existing.id,
            "api_key": existing.api_key,
            "plan": existing.plan.value
        }
    
    customer = billing.create_customer(data.email, data.name)
    
    return {
        "message": "Customer created",
        "customer_id": customer.id,
        "api_key": customer.api_key,
        "plan": customer.plan.value
    }


@billing_router.post("/checkout")
async def create_checkout(data: CheckoutRequest):
    """
    Create a Stripe Checkout session for subscription.
    
    Returns checkout URL to redirect user.
    """
    billing = get_billing()
    
    if not billing or not billing.is_enabled:
        raise HTTPException(503, "Stripe billing not configured")
    
    try:
        plan = SubscriptionPlan(data.plan)
    except ValueError:
        raise HTTPException(400, f"Invalid plan: {data.plan}")
    
    if plan == SubscriptionPlan.SPARK:
        raise HTTPException(400, "Spark plan is free and doesn't require payment")
    
    result = billing.create_checkout_session(
        customer_email=data.email,
        plan=plan,
        success_url=data.success_url,
        cancel_url=data.cancel_url,
        trial_days=data.trial_days
    )
    
    if not result.success:
        raise HTTPException(400, result.error)
    
    return {
        "checkout_url": result.checkout_url,
        "session_id": result.session_id
    }


@billing_router.get("/portal")
async def customer_portal(
    x_api_key: str = Header(...),
    return_url: str = "https://photonpath.io"
):
    """
    Get Stripe Customer Portal URL for subscription management.
    
    Customers can:
    - Update payment method
    - Cancel subscription
    - View invoices
    """
    billing = get_billing()
    
    if not billing or not billing.is_enabled:
        raise HTTPException(503, "Stripe billing not configured")
    
    customer = billing.get_customer_by_api_key(x_api_key)
    if not customer:
        raise HTTPException(404, "Customer not found")
    
    portal_url = billing.create_portal_session(customer.id, return_url)
    
    if not portal_url:
        raise HTTPException(400, "Could not create portal session")
    
    return {"portal_url": portal_url}


@billing_router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint.
    
    Configure in Stripe Dashboard:
    https://dashboard.stripe.com/webhooks
    
    Events to enable:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    billing = get_billing()
    
    if not billing or not billing.is_enabled:
        raise HTTPException(503, "Stripe not configured")
    
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    
    result = billing.handle_webhook(payload, signature)
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Webhook processing failed"))
    
    return result


@billing_router.get("/validate")
async def validate_api_key(x_api_key: str = Header(...)):
    """
    Validate an API key and get customer info.
    
    Returns:
    - Customer ID
    - Email
    - Current plan
    - Rate limits
    """
    billing = get_billing()
    
    if not billing:
        # Fallback for demo keys
        demo_keys = {
            "demo_key_12345": {"plan": "free", "status": "demo"},
            "sk_research_demo": {"plan": "research", "status": "demo"},
            "sk_pro_demo_key": {"plan": "pro", "status": "demo"}
        }
        if x_api_key in demo_keys:
            return {
                "valid": True,
                **demo_keys[x_api_key],
                "limits": PLAN_LIMITS.get(Plan(demo_keys[x_api_key]["plan"]))
            }
        raise HTTPException(401, "Invalid API key")
    
    customer_info = billing.validate_api_key(x_api_key)
    
    if not customer_info:
        raise HTTPException(401, "Invalid API key")
    
    return {
        "valid": True,
        **customer_info
    }


# ============================================================================
# EXAMPLE: HOW TO ADD TO API
# ============================================================================

"""
In api_v2.py, add:

# At imports
from billing_endpoints import (
    billing_router, 
    usage_router, 
    init_billing_system,
    rate_limit_check
)

# At startup
@app.on_event("startup")
async def startup():
    init_billing_system(
        redis_url=os.getenv("REDIS_URL"),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET")
    )

# Include routers
app.include_router(billing_router)
app.include_router(usage_router)

# Add rate limiting to endpoints
@app.get("/v2/tissues/{tissue_id}")
async def get_tissue(
    tissue_id: str,
    wavelength: float,
    user: dict = Depends(rate_limit_check)  # <-- Add this
):
    ...
"""
