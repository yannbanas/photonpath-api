"""
Génère une URL de checkout Stripe complète
"""
import os
from dotenv import load_dotenv
load_dotenv()

from stripe_billing import init_billing, SubscriptionPlan

# Init
billing = init_billing()

if not billing.is_enabled:
    print("❌ Stripe non configuré")
    exit(1)

print("="*60)
print("💳 Génération d'URL de Checkout")
print("="*60)

# Générer pour chaque plan
for plan in [SubscriptionPlan.PHOTON, SubscriptionPlan.BEAM, SubscriptionPlan.LASER]:
    result = billing.create_checkout_session(
        customer_email="test@photonpath.io",
        plan=plan,
        success_url="https://photonpath.io/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://photonpath.io/cancel",
        trial_days=14
    )
    
    if result.success:
        print(f"\n🔗 {plan.value.upper()} ({plan.value}):")
        print(f"   {result.checkout_url}")
    else:
        print(f"\n❌ {plan.value}: {result.error}")

print("\n" + "="*60)
print("💡 Copie une URL complète et ouvre-la dans ton navigateur")
print("💳 Carte test: 4242 4242 4242 4242 | Date: 12/34 | CVC: 123")
print("="*60)
