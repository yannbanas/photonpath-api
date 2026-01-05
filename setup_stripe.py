"""
PhotonPath - Setup Stripe Products & Prices
============================================

Ce script crée les produits et prix sur ton compte Stripe.
À exécuter UNE SEULE FOIS pour initialiser.

Usage:
    python setup_stripe.py

Author: PhotonPath
"""

import os
import stripe
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# Configurer Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key:
    print("❌ STRIPE_SECRET_KEY non trouvée dans .env")
    exit(1)

print("="*60)
print("🔧 PhotonPath - Configuration Stripe")
print("="*60)

if stripe.api_key.startswith("sk_test_"):
    print("📋 Mode: TEST")
elif stripe.api_key.startswith("sk_live_"):
    print("📋 Mode: LIVE ⚠️ ATTENTION - Données réelles!")
    confirm = input("Continuer en mode LIVE ? (oui/non): ")
    if confirm.lower() != "oui":
        print("Annulé.")
        exit(0)

# ============================================================================
# DÉFINITION DES PRODUITS
# ============================================================================

PRODUCTS = {
    "photon": {
        "name": "PhotonPath Photon",
        "emoji": "💡",
        "description": "Plan Doctorants & petits projets - 2,000 requêtes/jour",
        "price_monthly": 2900,  # En centimes (29.00€)
        "price_yearly": 29000,  # 290€/an (2 mois gratuits)
        "features": [
            "2,000 API requests/day",
            "100 Monte Carlo simulations/day",
            "Full tissue database (35 tissues)",
            "PDT Dosimetry included",
            "Email support"
        ]
    },
    "beam": {
        "name": "PhotonPath Beam",
        "emoji": "🔦",
        "description": "Plan Chercheurs académiques - 15,000 requêtes/jour",
        "price_monthly": 9900,  # 99€/mois
        "price_yearly": 99000,  # 990€/an
        "features": [
            "15,000 API requests/day",
            "1,000 Monte Carlo simulations/day",
            "Full tissue database",
            "Batch processing (100 items)",
            "Priority email support",
            "API Analytics dashboard"
        ]
    },
    "laser": {
        "name": "PhotonPath Laser",
        "emoji": "⚡",
        "description": "Plan Entreprises & startups - 100,000 requêtes/jour",
        "price_monthly": 29900,  # 299€/mois
        "price_yearly": 299000,  # 2990€/an
        "features": [
            "100,000 API requests/day",
            "10,000 Monte Carlo simulations/day",
            "Custom tissue uploads",
            "Batch processing (500 items)",
            "Dedicated support",
            "Advanced API Analytics"
        ]
    },
    "fusion": {
        "name": "PhotonPath Fusion",
        "emoji": "🌟",
        "description": "Plan Pharma, hôpitaux, OEM - Sur devis",
        "price_monthly": 99900,  # 999€/mois (placeholder pour affichage)
        "price_yearly": 999000,
        "features": [
            "Unlimited API requests",
            "Unlimited Monte Carlo + GPU",
            "Custom tissue database",
            "Dedicated support + SLA",
            "On-premise deployment option",
            "Custom integrations"
        ]
    }
}

# ============================================================================
# CRÉATION DES PRODUITS ET PRIX
# ============================================================================

created_prices = {}

for plan_id, plan_data in PRODUCTS.items():
    print(f"\n{'='*40}")
    print(f"📦 Création: {plan_data['name']}")
    print(f"{'='*40}")
    
    # Vérifier si le produit existe déjà
    existing_products = stripe.Product.list(limit=100)
    existing = None
    for p in existing_products.data:
        if p.name == plan_data['name']:
            existing = p
            break
    
    if existing:
        print(f"   ⚠️ Produit existe déjà: {existing.id}")
        product = existing
    else:
        # Créer le produit
        product = stripe.Product.create(
            name=plan_data['name'],
            description=plan_data['description'],
            metadata={
                "plan_id": plan_id,
                "features": ", ".join(plan_data['features'][:3])
            }
        )
        print(f"   ✅ Produit créé: {product.id}")
    
    # Créer le prix mensuel
    print(f"\n   💰 Prix mensuel: {plan_data['price_monthly']/100:.2f}€")
    
    # Vérifier si le prix existe
    existing_prices = stripe.Price.list(product=product.id, limit=10)
    monthly_exists = False
    yearly_exists = False
    
    for price in existing_prices.data:
        if price.recurring and price.recurring.interval == "month":
            monthly_exists = True
            created_prices[f"{plan_id}_monthly"] = price.id
            print(f"   ⚠️ Prix mensuel existe: {price.id}")
        if price.recurring and price.recurring.interval == "year":
            yearly_exists = True
            created_prices[f"{plan_id}_yearly"] = price.id
            print(f"   ⚠️ Prix annuel existe: {price.id}")
    
    if not monthly_exists:
        price_monthly = stripe.Price.create(
            product=product.id,
            unit_amount=plan_data['price_monthly'],
            currency="eur",
            recurring={"interval": "month"},
            metadata={"plan_id": plan_id, "billing": "monthly"}
        )
        created_prices[f"{plan_id}_monthly"] = price_monthly.id
        print(f"   ✅ Prix mensuel créé: {price_monthly.id}")
    
    # Créer le prix annuel
    print(f"   💰 Prix annuel: {plan_data['price_yearly']/100:.2f}€")
    
    if not yearly_exists:
        price_yearly = stripe.Price.create(
            product=product.id,
            unit_amount=plan_data['price_yearly'],
            currency="eur",
            recurring={"interval": "year"},
            metadata={"plan_id": plan_id, "billing": "yearly"}
        )
        created_prices[f"{plan_id}_yearly"] = price_yearly.id
        print(f"   ✅ Prix annuel créé: {price_yearly.id}")

# ============================================================================
# CRÉER UN CLIENT DE TEST
# ============================================================================

print(f"\n{'='*60}")
print("👤 Création d'un client de test")
print("="*60)

test_customer = stripe.Customer.create(
    email="test@photonpath.io",
    name="Test User PhotonPath",
    metadata={
        "source": "setup_script",
        "plan": "free"
    }
)
print(f"✅ Client créé: {test_customer.id}")
print(f"   Email: {test_customer.email}")

# ============================================================================
# RÉSUMÉ
# ============================================================================

print(f"\n{'='*60}")
print("📋 RÉSUMÉ - IDs à mettre dans stripe_billing.py")
print("="*60)

print("\nSTRIPE_PRICES = {")
print('    SubscriptionPlan.SPARK: None,  # Gratuit')
for plan_id in ["photon", "beam", "laser", "fusion"]:
    monthly_id = created_prices.get(f"{plan_id}_monthly", "price_xxx")
    print(f'    SubscriptionPlan.{plan_id.upper()}: "{monthly_id}",')
print("}")

print(f"\n{'='*60}")
print("✅ Configuration Stripe terminée !")
print("="*60)
print("\n📌 Prochaines étapes:")
print("   1. Va sur https://dashboard.stripe.com/test/products")
print("   2. Vérifie que les 3 produits sont créés")
print("   3. Copie les Price IDs dans stripe_billing.py")
print("   4. Configure le webhook (optionnel pour test)")

# Sauvegarder les IDs dans un fichier
with open("stripe_price_ids.txt", "w") as f:
    f.write("# PhotonPath Stripe Price IDs\n")
    f.write("# Copie ces valeurs dans stripe_billing.py\n\n")
    for key, value in created_prices.items():
        f.write(f"{key}={value}\n")
    f.write(f"\ntest_customer_id={test_customer.id}\n")

print(f"\n💾 IDs sauvegardés dans: stripe_price_ids.txt")
