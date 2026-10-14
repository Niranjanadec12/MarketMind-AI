from backend.app.ai.recommendation_engine import (
    ProductRecommendationEngine,
)

engine = ProductRecommendationEngine()

print("Training product recommendation engine...")
summary = engine.fit()

print("\n===== TRAINING SUMMARY =====")
for key, value in summary.items():
    print(f"{key}: {value}")

print("\n===== POPULAR PRODUCTS =====")
for item in engine.get_popular_products(n=5):
    print(item)

print("\n===== SIMILAR PRODUCT RECOMMENDATIONS =====")
popular = engine.get_popular_products(n=1)

if popular:
    product_id = popular[0]["product_id"]
    print("Selected product:", product_id)

    for item in engine.recommend_similar_products(
        product_id, n=5
    ):
        print(item)

print("\n===== CUSTOMER RECOMMENDATION TEST =====")

customer_id = next(
    (
        customer
        for customer, products in engine.customer_products.items()
        if len(products) >= 2
    ),
    None,
)

if customer_id:
    print("Test customer:", customer_id)
    print(
        "Previously purchased products:",
        engine.customer_products[customer_id],
    )

    for item in engine.recommend_for_customer(
        customer_id, n=5
    ):
        print(item)
else:
    print("No customer with multiple products was found.")

print("\nRecommendation engine tests completed.")
