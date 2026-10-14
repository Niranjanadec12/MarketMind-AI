
from pathlib import Path

import pandas as pd

from backend.app.ai.recommendation_engine import (
    ProductRecommendationEngine,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = PROJECT_ROOT / "data" / "analytical"

PRODUCTS_PATH = PROJECT_ROOT / "data" / "processed" / "products_cleaned.csv"
RULES_PATH = DATA_DIR / "product_association_rules.csv"
SALES_PATH = DATA_DIR / "sales_analytics.csv"
OUTPUT_PATH = DATA_DIR / "customer_sales_suggestions.csv"

OUTPUT_COLUMNS = [
    "source_products",
    "product_id",
    "score",
    "confidence",
    "lift",
    "support",
    "pair_count",
    "category",
    "reason",
    "suggestion_type",
]


def load_association_rules():
    if not RULES_PATH.exists():
        raise FileNotFoundError(
            f"Association rules not found: {RULES_PATH}. "
            "Run association_rules.py first."
        )

    rules = pd.read_csv(RULES_PATH)

    required = {
        "antecedents",
        "consequents",
        "confidence",
        "lift",
    }
    missing = required - set(rules.columns)

    if missing:
        raise ValueError(
            f"Association rules file is missing columns: "
            f"{sorted(missing)}"
        )

    # Remove incomplete or invalid rules.
    rules = rules.dropna(
        subset=["antecedents", "consequents", "confidence", "lift"]
    ).copy()

    rules["antecedents"] = rules["antecedents"].astype(str)
    rules["consequents"] = rules["consequents"].astype(str)

    # Pre-parse rules once rather than parsing them for every order.
    parsed_rules = []

    for _, rule in rules.iterrows():
        antecedents = {
            item.strip()
            for item in rule["antecedents"].split("|")
            if item.strip()
        }
        consequents = {
            item.strip()
            for item in rule["consequents"].split("|")
            if item.strip()
        }

        if not antecedents or not consequents:
            continue

        parsed_rules.append({
            "antecedents": antecedents,
            "consequents": consequents,
            "confidence": float(rule["confidence"]),
            "lift": float(rule["lift"]),
            "support": float(rule.get("support", 0)),
            "pair_count": int(rule.get("pair_count", 0)),
        })

    return parsed_rules


def get_cross_sell_suggestions(purchased_products, rules, limit=5):
    """Suggest products associated with items already purchased."""

    purchased = {str(product) for product in purchased_products}
    suggestions = {}

    for rule in rules:
        antecedents = rule["antecedents"]
        consequents = rule["consequents"]

        if not antecedents.issubset(purchased):
            continue

        for product in consequents - purchased:
            # Use confidence as the score. Lift can be inflated when
            # a product is extremely rare, so retain it as a metric
            # instead of multiplying it into the recommendation score.
            score = rule["confidence"]

            candidate = {
                "product_id": product,
                "score": round(score, 6),
                "confidence": rule["confidence"],
                "lift": rule["lift"],
                "support": rule["support"],
                "pair_count": rule["pair_count"],
                "category": "Unknown",
                "reason": (
                    "Association rule triggered by purchased product(s): "
                    + ", ".join(sorted(antecedents))
                ),
                "suggestion_type": "cross_sell",
            }

            # Keep the strongest-confidence rule for each product.
            current = suggestions.get(product)

            if (
                current is None
                or candidate["confidence"] > current["confidence"]
                or (
                    candidate["confidence"] == current["confidence"]
                    and candidate["pair_count"] > current["pair_count"]
                )
            ):
                suggestions[product] = candidate

    return sorted(
        suggestions.values(),
        key=lambda item: (
            item["confidence"],
            item["pair_count"],
            item["support"],
        ),
        reverse=True,
    )[:limit]


def get_related_product_suggestions(
    purchased_products, engine, limit=5
):
    """Find related products, not verified price-based upsells."""

    purchased = {str(product) for product in purchased_products}
    scores = {}

    for product in purchased:
        candidates = engine.recommend_similar_products(
            product, n=limit + len(purchased)
        )

        for suggestion in candidates:
            candidate = str(suggestion["product_id"])

            if candidate in purchased:
                continue

            score = float(suggestion["score"])

            if (
                candidate not in scores
                or score > scores[candidate]["score"]
            ):
                scores[candidate] = {
                    "product_id": candidate,
                    "score": score,
                    "confidence": None,
                    "lift": None,
                    "support": None,
                    "pair_count": None,
                    "category": suggestion.get(
                        "category", "Unknown"
                    ),
                    "reason": (
                        f"Related to purchased product {product}; "
                        "consider as an alternative"
                    ),
                    "suggestion_type": "related_product",
                }

    return sorted(
        scores.values(),
        key=lambda item: item["score"],
        reverse=True,
    )[:limit]


def load_product_categories():
    if not PRODUCTS_PATH.exists():
        print("Product metadata not found; categories will use Unknown.")
        return {}

    products = pd.read_csv(
        PRODUCTS_PATH,
        usecols=["product_id", "product_category_name"],
    ).dropna(subset=["product_id"])

    return dict(
        zip(
            products["product_id"].astype(str),
            products["product_category_name"].fillna("Unknown"),
        )
    )


def main():
    rules = load_association_rules()

    if not rules:
        print("No usable association rules were found.")

    print("Loading recommendation engine...")
    engine = ProductRecommendationEngine()
    engine.fit()

    print("Loading delivered sales...")
    sales = pd.read_csv(
        SALES_PATH,
        usecols=["order_id", "product_id", "order_status"],
    )

    delivered = sales[
        sales["order_status"].eq("delivered")
    ].dropna(subset=["order_id", "product_id"])

    baskets = delivered.groupby("order_id")["product_id"].apply(
        lambda values: sorted(set(values.astype(str)))
    )

    # Quickly skip orders that cannot trigger any rule.
    antecedent_products = set()

    for rule in rules:
        antecedent_products.update(rule["antecedents"])

    example_basket = None
    cross_sell = []

    # Prefer a real basket that produces at least one cross-sell.
    for basket in baskets:
        if len(basket) < 2:
            continue

        if not (set(basket) & antecedent_products):
            continue

        candidate_suggestions = get_cross_sell_suggestions(
            basket, rules, limit=5
        )

        if candidate_suggestions:
            example_basket = basket
            cross_sell = candidate_suggestions
            break

    if example_basket is None:
        # Graceful fallback if no basket triggers a usable rule.
        example_basket = next(
            (basket for basket in baskets if len(basket) >= 2),
            None,
        )

    if example_basket is None:
        print("No multi-product delivered order was found.")
        return

    related = get_related_product_suggestions(
        example_basket, engine, limit=5
    )

    product_categories = load_product_categories()

    for item in cross_sell:
        item["category"] = product_categories.get(
            item["product_id"], "Unknown"
    )

    source_products = " | ".join(example_basket)
    records = []

    for item in cross_sell:
        records.append({
            "source_products": source_products,
            **item,
        })

    for item in related:
        records.append({
            "source_products": source_products,
            **item,
        })

    output = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)

    print("\n===== EXAMPLE PURCHASE =====")
    print(example_basket)

    print("\n===== CROSS-SELL SUGGESTIONS =====")
    if cross_sell:
        print(pd.DataFrame(cross_sell).to_string(index=False))
    else:
        print("No matching association rules for this basket.")

    print("\n===== RELATED-PRODUCT CANDIDATES =====")
    if related:
        print(pd.DataFrame(related).to_string(index=False))
    else:
        print("No related products found.")

    print(f"\nSaved suggestions to: {OUTPUT_PATH}")
    print(f"Total suggestion rows: {len(output)}")
    print(
        "Cross-sell rows:",
        int((output["suggestion_type"] == "cross_sell").sum()),
    )
    print(
        "Related-product rows:",
        int((output["suggestion_type"] == "related_product").sum()),
    )


if __name__ == "__main__":
    main()
