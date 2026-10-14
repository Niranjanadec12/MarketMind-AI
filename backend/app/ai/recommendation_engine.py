
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import math

import pandas as pd


# Project root: MarketMind-AI/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

SALES_PATH = (
    PROJECT_ROOT / "data" / "analytical" / "sales_analytics.csv"
)
CUSTOMERS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "customers_clean.csv"
)


class ProductRecommendationEngine:
    """
    Hybrid product recommendation engine.

    - Uses delivered purchases only.
    - Maps order-scoped customer IDs to actual customer identities.
    - Builds product-to-product similarities from customer purchase history.
    - Uses popular products as a fallback when evidence is insufficient.
    """

    def __init__(self):
        self.is_trained = False
        self.customer_products = {}
        self.product_customer_counts = Counter()
        self.product_popularity = Counter()
        self.product_categories = {}
        self.product_similarities = defaultdict(dict)

    def fit(self):
        """Load purchase data and build recommendation statistics."""

        if not SALES_PATH.exists():
            raise FileNotFoundError(
                f"Sales dataset not found: {SALES_PATH}"
            )

        if not CUSTOMERS_PATH.exists():
            raise FileNotFoundError(
                f"Customer mapping not found: {CUSTOMERS_PATH}"
            )

        sales = pd.read_csv(
            SALES_PATH,
            usecols=[
                "order_id",
                "customer_id",
                "product_id",
                "order_status",
                "product_category_name_english",
            ],
        )

        customers = pd.read_csv(
            CUSTOMERS_PATH,
            usecols=["customer_id", "customer_unique_id"],
        )

        # Keep only completed purchases.
        sales = sales[
            sales["order_status"].eq("delivered")
        ].copy()

        # Normalize identifiers and discard invalid rows.
        sales = sales.dropna(
            subset=["customer_id", "product_id"]
        )
        customers = customers.dropna(
            subset=["customer_id", "customer_unique_id"]
        )

        sales["customer_id"] = sales["customer_id"].astype(str)
        sales["product_id"] = sales["product_id"].astype(str)
        customers["customer_id"] = customers["customer_id"].astype(str)
        customers["customer_unique_id"] = (
            customers["customer_unique_id"].astype(str)
        )

        # Convert order-scoped IDs into actual customer identities.
        data = sales.merge(
            customers,
            on="customer_id",
            how="left",
            validate="many_to_one",
        )

        data = data.dropna(subset=["customer_unique_id"])

        # Count product purchases for the popularity fallback.
        self.product_popularity = Counter(
            data["product_id"].value_counts().to_dict()
        )

        # Store a representative English category for each product.
        if "product_category_name_english" in data.columns:
            category_rows = data.dropna(
                subset=["product_category_name_english"]
            )

            self.product_categories = (
                category_rows.groupby("product_id")[
                    "product_category_name_english"
                ]
                .agg(lambda values: values.mode().iloc[0])
                .to_dict()
            )

        # Deduplicate customer-product interactions.
        interactions = data[
            ["customer_unique_id", "product_id"]
        ].drop_duplicates()

        self.customer_products = (
            interactions.groupby("customer_unique_id")["product_id"]
            .apply(set)
            .to_dict()
        )

        # Number of distinct actual customers who bought each product.
        self.product_customer_counts = Counter(
            interactions["product_id"].value_counts().to_dict()
        )

        # Build product similarities from shared customer histories.
        pair_counts = Counter()

        for products in self.customer_products.values():
            if len(products) < 2:
                continue

            for product_a, product_b in combinations(
                sorted(products), 2
            ):
                pair_counts[(product_a, product_b)] += 1

        # Cosine-style similarity:
        # shared customers / sqrt(customers_A * customers_B)
        for (product_a, product_b), shared_count in pair_counts.items():
            count_a = self.product_customer_counts[product_a]
            count_b = self.product_customer_counts[product_b]

            denominator = math.sqrt(count_a * count_b)

            if denominator == 0:
                continue

            similarity = shared_count / denominator

            self.product_similarities[product_a][product_b] = similarity
            self.product_similarities[product_b][product_a] = similarity

        self.is_trained = True

        return {
            "delivered_line_items": len(data),
            "actual_customers": len(self.customer_products),
            "products": len(self.product_popularity),
            "customer_product_interactions": len(interactions),
            "customers_with_multiple_products": sum(
                len(products) > 1
                for products in self.customer_products.values()
            ),
            "product_pairs_with_shared_customers": len(pair_counts),
        }

    def _require_trained(self):
        if not self.is_trained:
            raise RuntimeError(
                "Recommendation engine is not trained. Call fit() first."
            )

    def _product_result(self, product_id, score, reason):
        return {
            "product_id": product_id,
            "score": round(float(score), 6),
            "category": self.product_categories.get(
                product_id, "Unknown"
            ),
            "reason": reason,
        }

    def get_popular_products(self, n=10, exclude=None):
        """Return the most frequently purchased delivered products."""

        self._require_trained()
        exclude = set(exclude or [])

        results = []

        for product_id, count in self.product_popularity.most_common():
            if product_id in exclude:
                continue

            results.append(
                self._product_result(
                    product_id,
                    count,
                    "Popular among delivered purchases",
                )
            )

            if len(results) >= n:
                break

        return results

    def recommend_for_customer(self, customer_unique_id, n=5):
        """
        Recommend products using the customer's historical purchases.

        customer_unique_id must be an ID from the Olist customer dataset,
        not a MarketMind application account ID.
        """

        self._require_trained()

        customer_unique_id = str(customer_unique_id)
        purchased = self.customer_products.get(customer_unique_id, set())

        if not purchased:
            return self.get_popular_products(n=n)

        scores = defaultdict(float)

        # Combine similarities from all products in the customer's history.
        for purchased_product in purchased:
            for candidate, similarity in (
                self.product_similarities.get(
                    purchased_product, {}
                ).items()
            ):
                if candidate not in purchased:
                    scores[candidate] += similarity

        ranked = sorted(
            scores.items(),
            key=lambda item: (
                item[1],
                self.product_customer_counts[item[0]],
            ),
            reverse=True,
        )

        results = [
            self._product_result(
                product_id,
                score,
                "Related to products in the customer's purchase history",
            )
            for product_id, score in ranked[:n]
        ]

        # Fill any remaining slots with popular products.
        if len(results) < n:
            already_selected = purchased | {
                item["product_id"] for item in results
            }

            results.extend(
                self.get_popular_products(
                    n=n - len(results),
                    exclude=already_selected,
                )
            )

        return results[:n]

    def recommend_similar_products(self, product_id, n=5):
        """Recommend products bought by customers with similar histories."""

        self._require_trained()
        product_id = str(product_id)

        similarities = self.product_similarities.get(product_id, {})

        ranked = sorted(
            similarities.items(),
            key=lambda item: (
                item[1],
                self.product_customer_counts[item[0]],
            ),
            reverse=True,
        )

        results = [
            self._product_result(
                candidate,
                score,
                "Purchased by customers who also bought the selected product",
            )
            for candidate, score in ranked[:n]
        ]

        if len(results) < n:
            excluded = {product_id} | {
                item["product_id"] for item in results
            }

            results.extend(
                self.get_popular_products(
                    n=n - len(results),
                    exclude=excluded,
                )
            )

        return results[:n]
