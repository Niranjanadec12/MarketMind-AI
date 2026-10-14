
from pathlib import Path
from collections import Counter
from itertools import combinations

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SALES_PATH = PROJECT_ROOT / "data" / "analytical" / "sales_analytics.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "analytical"

RULES_PATH = OUTPUT_DIR / "product_association_rules.csv"
ITEMSETS_PATH = OUTPUT_DIR / "frequent_product_itemsets.csv"


def run_association_analysis(min_pair_count=3, min_confidence=0.05):
    print("Loading delivered sales...")

    sales = pd.read_csv(
        SALES_PATH,
        usecols=["order_id", "product_id", "order_status"],
    )

    sales = sales[
        (sales["order_status"] == "delivered")
    ].dropna(subset=["order_id", "product_id"])

    # One basket per order; count each product only once per order.
    baskets = (
        sales.groupby("order_id")["product_id"]
        .apply(lambda values: sorted(set(values.astype(str))))
    )

    total_orders = len(baskets)

    if total_orders == 0:
        print("No delivered orders found.")
        return

    print(f"Delivered order baskets: {total_orders:,}")

    # Count individual product occurrences and co-occurring product pairs.
    product_counts = Counter()
    pair_counts = Counter()

    for basket in baskets:
        product_counts.update(basket)

        if len(basket) >= 2:
            pair_counts.update(combinations(basket, 2))

    print(f"Unique products: {len(product_counts):,}")
    print(f"Product pairs found: {len(pair_counts):,}")

    # Export frequent single products and product pairs.
    itemset_rows = []

    for product, count in product_counts.items():
        itemset_rows.append({
            "itemsets": product,
            "itemset_size": 1,
            "count": count,
            "support": count / total_orders,
        })

    for (product_a, product_b), count in pair_counts.items():
        if count >= min_pair_count:
            itemset_rows.append({
                "itemsets": f"{product_a} | {product_b}",
                "itemset_size": 2,
                "count": count,
                "support": count / total_orders,
            })

    itemsets_df = pd.DataFrame(itemset_rows)
    itemsets_df.to_csv(ITEMSETS_PATH, index=False)

    # Build directional association rules: A -> B and B -> A.
    rule_rows = []

    for (product_a, product_b), pair_count in pair_counts.items():
        if pair_count < min_pair_count:
            continue

        support = pair_count / total_orders

        directions = [
            (product_a, product_b),
            (product_b, product_a),
        ]

        for antecedent, consequent in directions:
            confidence = pair_count / product_counts[antecedent]
            consequent_support = (
                product_counts[consequent] / total_orders
            )
            lift = confidence / consequent_support

            if confidence < min_confidence:
                continue

            rule_rows.append({
                "antecedents": antecedent,
                "consequents": consequent,
                "support": support,
                "confidence": confidence,
                "lift": lift,
                "pair_count": pair_count,
            })

    rules_df = pd.DataFrame(
        rule_rows,
        columns=[
            "antecedents",
            "consequents",
            "support",
            "confidence",
            "lift",
            "pair_count",
        ],
    )

    if not rules_df.empty:
        rules_df = rules_df.sort_values(
            ["lift", "confidence", "support"],
            ascending=False,
        )

    rules_df.to_csv(RULES_PATH, index=False)

    print("\n===== ASSOCIATION ANALYSIS RESULTS =====")
    print(f"Delivered orders analyzed: {total_orders:,}")
    print(f"Unique products: {len(product_counts):,}")
    print(f"Product pairs meeting minimum count: "
          f"{sum(c >= min_pair_count for c in pair_counts.values()):,}")
    print(f"Association rules generated: {len(rules_df):,}")
    print(f"Saved itemsets: {ITEMSETS_PATH}")
    print(f"Saved association rules: {RULES_PATH}")

    if not rules_df.empty:
        print("\n===== TOP 10 ASSOCIATION RULES =====")
        print(rules_df.head(10).to_string(index=False))
    else:
        print(
            "\nNo rules met the thresholds. This may mean "
            "too few orders contain multiple products."
        )


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_association_analysis()
