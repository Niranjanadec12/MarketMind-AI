
from backend.app.ai.recommendation_engine import ProductRecommendationEngine

engine = ProductRecommendationEngine()
print("Training recommendation engine...")
summary = engine.fit()

print("\n===== TRAINING SUMMARY =====")
for key, value in summary.items():
    print(f"{key}: {value}")

print("\n===== AUTOMATED VALIDATION =====")

popular = engine.get_popular_products(n=10)
assert len(popular) == 10
assert len({p["product_id"] for p in popular}) == 10
print("PASS: 10 unique popular products returned")

source_product = popular[0]["product_id"]
similar = engine.recommend_similar_products(source_product, n=5)

assert len(similar) == 5
assert all(p["product_id"] != source_product for p in similar)
assert len({p["product_id"] for p in similar}) == len(similar)
print("PASS: Similar-product results are unique and exclude the source")

test_customers = [
    (customer_id, products)
    for customer_id, products in engine.customer_products.items()
    if len(products) >= 2
][:20]

assert test_customers, "No eligible customers found"

for customer_id, purchased in test_customers:
    recommendations = engine.recommend_for_customer(customer_id, n=5)
    recommended_ids = {item["product_id"] for item in recommendations}

    assert len(recommendations) == 5, (
        f"Wrong number of recommendations for {customer_id}"
    )
    assert len(recommended_ids) == 5, (
        f"Duplicate recommendations for {customer_id}"
    )
    assert not (recommended_ids & purchased), (
        f"Previously purchased product recommended to {customer_id}"
    )

print(
    f"PASS: {len(test_customers)} customers received "
    "5 unique recommendations without previously purchased products"
)

print("\nALL VALIDATION CHECKS PASSED")
