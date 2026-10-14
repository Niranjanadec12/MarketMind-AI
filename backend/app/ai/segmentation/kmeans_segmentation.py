import pandas as pd
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

from app.ai.segmentation.data_preparation import (
    prepare_segmentation_features
)


def run_kmeans_segmentation(n_clusters=3):
    """
    Run K-Means clustering on customer segmentation features.
    """

    # ---------------------------------------------------------
    # 1. Prepare customer features
    # ---------------------------------------------------------

    features = prepare_segmentation_features()

    # ---------------------------------------------------------
    # 2. Select features for clustering
    # ---------------------------------------------------------

    clustering_features = features[
        [
            "purchase_frequency",
            "purchase_value",
            "customer_activity"
        ]
    ].copy()

    # ---------------------------------------------------------
    # 3. Scale the features
    # ---------------------------------------------------------

    scaler = StandardScaler()

    scaled_features = scaler.fit_transform(
        clustering_features
    )

    # ---------------------------------------------------------
    # 4. Create K-Means model
    # ---------------------------------------------------------

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    # ---------------------------------------------------------
    # 5. Generate cluster labels
    # ---------------------------------------------------------

    features["cluster"] = kmeans.fit_predict(
        scaled_features
    )

    return features, kmeans


def save_segmentation_results(features):
    """
    Save K-Means segmentation results.
    """

    project_root = Path(__file__).resolve().parents[4]

    output_directory = (
        project_root / "data" / "analytical"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_directory /
        "customer_segments_kmeans.csv"
    )

    features.to_csv(
        output_file,
        index=False
    )

    return output_file


if __name__ == "__main__":

    print("\n===== K-MEANS CUSTOMER SEGMENTATION =====")

    features, model = run_kmeans_segmentation(
        n_clusters=3
    )

    # ---------------------------------------------------------
    # Basic information
    # ---------------------------------------------------------

    print(f"\nCustomers clustered: {len(features)}")

    print(
        f"Number of clusters: "
        f"{features['cluster'].nunique()}"
    )

    # ---------------------------------------------------------
    # Cluster distribution
    # ---------------------------------------------------------

    print("\n===== CLUSTER DISTRIBUTION =====")

    print(
        features["cluster"]
        .value_counts()
        .sort_index()
    )

    # ---------------------------------------------------------
    # Cluster characteristics
    # ---------------------------------------------------------

    print("\n===== CLUSTER CHARACTERISTICS =====")

    cluster_summary = (
        features
        .groupby("cluster")[
            [
                "purchase_frequency",
                "purchase_value",
                "customer_activity"
            ]
        ]
        .mean()
        .round(2)
    )

    print(cluster_summary)

    # ---------------------------------------------------------
    # Save results
    # ---------------------------------------------------------

    output_file = save_segmentation_results(
        features
    )

    print(
        f"\nResults saved to:\n{output_file}"
    )