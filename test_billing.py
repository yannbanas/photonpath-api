"""
PhotonPath Billing & Rate Limiting Test Script
===============================================

Test the billing and rate limiting modules locally.

Usage:
    python test_billing.py
    
Author: PhotonPath
"""

import sys
import os

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using system env vars only")

def test_rate_limiter():
    """Test rate limiter module."""
    print("\n" + "="*50)
    print("🧪 Testing Rate Limiter")
    print("="*50)
    
    from rate_limiter import RateLimiter, Plan, PLAN_LIMITS
    
    # Test without Redis (in-memory)
    limiter = RateLimiter()
    print(f"✅ RateLimiter initialized (Redis: {limiter.is_redis})")
    
    # Test rate limiting
    api_key = "test_key_12345"
    
    # First request should pass
    result = limiter.check_rate_limit(api_key, Plan.SPARK)
    print(f"✅ First request: allowed={result.allowed}, remaining={result.remaining}")
    
    # Make many requests to test limit
    for i in range(10):
        result = limiter.check_rate_limit(api_key, Plan.SPARK)
    
    print(f"✅ After 10 requests: remaining={result.remaining}")
    
    # Test usage stats
    usage = limiter.get_usage(api_key, Plan.SPARK)
    print(f"✅ Usage stats: {usage['daily']['used']}/{usage['daily']['limit']} daily")
    
    # Test different plans
    for plan in Plan:
        limits = PLAN_LIMITS[plan]
        print(f"   {plan.value}: {limits['requests_per_day']}/day, {limits['requests_per_minute']}/min")
    
    print("✅ Rate limiter tests passed!")
    return True


def test_stripe_billing():
    """Test Stripe billing module."""
    print("\n" + "="*50)
    print("🧪 Testing Stripe Billing")
    print("="*50)
    
    from stripe_billing import (
        StripeBilling, 
        create_demo_customers,
        SubscriptionPlan,
        PLAN_FEATURES,
        _customers,
        _api_keys
    )
    
    # Initialize without Stripe keys (demo mode)
    billing = StripeBilling()
    print(f"✅ StripeBilling initialized (Stripe enabled: {billing.is_enabled})")
    
    # Create demo customers
    create_demo_customers()
    print(f"✅ Created {len(_customers)} demo customers")
    
    # Test customer lookup
    customer = billing.get_customer_by_api_key("demo_key_12345")
    if customer:
        print(f"✅ Found customer: {customer.email}, plan: {customer.plan.value}")
    
    # Test plan features
    plans = billing.get_plans()
    print(f"✅ Available plans: {len(plans)}")
    for plan in plans:
        print(f"   {plan['name']}: ${plan['price_monthly']}/mo - {plan['requests_per_day']}/day")
    
    # Test API key validation
    for api_key in ["demo_key_12345", "sk_research_demo", "sk_pro_demo_key"]:
        info = billing.validate_api_key(api_key)
        if info:
            print(f"✅ API key {api_key[:12]}... = {info['plan']} plan")
    
    print("✅ Stripe billing tests passed!")
    return True


def test_billing_endpoints():
    """Test billing API endpoints."""
    print("\n" + "="*50)
    print("🧪 Testing Billing Endpoints")
    print("="*50)
    
    from billing_endpoints import init_billing_system
    
    # Initialize billing system
    init_billing_system()
    print("✅ Billing system initialized")
    
    print("✅ Billing endpoints ready!")
    print("\nEndpoints available:")
    print("  GET  /usage/limits     - Get current usage")
    print("  GET  /usage/plans      - List all plans")
    print("  POST /billing/customers - Create customer")
    print("  POST /billing/checkout - Create checkout session")
    print("  GET  /billing/portal   - Customer portal URL")
    print("  POST /billing/webhook  - Stripe webhooks")
    print("  GET  /billing/validate - Validate API key")
    
    return True


def main():
    """Run all tests."""
    print("="*50)
    print("🔬 PhotonPath Billing & Rate Limiting Tests")
    print("="*50)
    
    tests = [
        ("Rate Limiter", test_rate_limiter),
        ("Stripe Billing", test_stripe_billing),
        ("Billing Endpoints", test_billing_endpoints),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} FAILED: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
