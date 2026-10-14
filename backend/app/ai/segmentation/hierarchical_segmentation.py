import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import pairwise_distances_argmin_min

from app.ai.segmentation.data_preparation import (
    prepare_segmentation_features
)


def run_hierarchical_segmentation(
    n_clusters=3,
    sample_size=5000,
    random_state=42
):
    """
    Perform hierarchical clustering on a representative sample
    and assign all customers to the resulting behavioral groups.
    """

    # Prepare all customer-level features
    all_features = prepare_segmentation_features()

    print(f"\nTotal customers available: {len(all_features)}")

    # Select representative sample for hierarchical clustering
    if len(all_features) > sample_size:
        sample_features = all_features.sample(
            n=sample_size,
            random_state=random_state
        ).copy()
    else:
        sample_features = all_features.copy()

    print(
        f"Customers used for hierarchical clustering: "
        f"{len(sample_features)}"
    )

    clustering_columns = [
        "purchase_frequency",
        "purchase_value",
        "customer_activity"
    ]

    # Extract sample clustering features
    sample_clustering_features = sample_features[
        clustering_columns
    ].copy()

    # Standardize using the sample
    scaler = StandardScaler()

    sample_scaled = scaler.fit_transform(
        sample_clustering_features
    )

    # Hierarchical clustering on the representative sample
    model = AgglomerativeClustering(
        n_clusters=n_clusters,
        linkage="ward"
    )

    sample_features["hierarchical_cluster"] = (
        model.fit_predict(sample_scaled)
    )

    # Calculate cluster centers in standardized feature space
    cluster_centers = (
        pd.DataFrame(
            sample_scaled,
            columns=clustering_columns
        )
        .assign(
            hierarchical_cluster=
            sample_features["hierarchical_cluster"].values
        )
        .groupby("hierarchical_cluster")[clustering_columns]
        .mean()
    )

    # Standardize ALL customers using the same scaler
    all_scaled = scaler.transform(
        all_features[clustering_columns]
    )

    # Find nearest hierarchical cluster center
    nearest_clusters, distances = (
        pairwise_distances_argmin_min(
            all_scaled,
            cluster_centers.loc[
                sorted(cluster_centers.index),
                clustering_columns
            ].values
        )
    )

    # Map nearest-center positions back to actual cluster labels
    cluster_labels = sorted(cluster_centers.index)

    all_features["hierarchical_cluster"] = [
        cluster_labels[index]
        for index in nearest_clusters
    ]

    return (
        all_features,
        sample_features,
        cluster_centers,
        scaler
    )


def add_segment_information(features):
    """
    Add meaningful business segment names and descriptions.
    """

    cluster_summary = (
        features.groupby("hierarchical_cluster")[
            [
                "purchase_frequency",
                "purchase_value",
                "customer_activity"
            ]
        ]
        .mean()
    )

    # Cluster with highest purchase frequency
    repeat_cluster = cluster_summary[
        "purchase_frequency"
    ].idxmax()

    remaining_clusters = [
        cluster
        for cluster in cluster_summary.index
        if cluster != repeat_cluster
    ]

    # Of the remaining clusters, the one with the
    # lowest activity value is the most recent.
    recent_cluster = cluster_summary.loc[
        remaining_clusters,
        "customer_activity"
    ].idxmin()

    # The remaining cluster is the inactive group.
    inactive_cluster = [
        cluster
        for cluster in remaining_clusters
        if cluster != recent_cluster
    ][0]

    segment_names = {
        recent_cluster: "Recent One-Time Customers",
        repeat_cluster: "Repeat High-Value Customers",
        inactive_cluster: "Inactive / Low-Value Customers"
    }

    segment_descriptions = {
        recent_cluster:
            "Customers with one purchase and relatively recent activity.",

        repeat_cluster:
            "Customers with multiple purchases and higher spending.",

        inactive_cluster:
            "Customers with one purchase, lower spending, and long inactivity."
    }

    features["segment_name"] = (
        features["hierarchical_cluster"]
        .map(segment_names)
    )

    features["segment_description"] = (
        features["hierarchical_cluster"]
        .map(segment_descriptions)
    )

    return features


def save_hierarchical_results(features):
    """
    Save final hierarchical segmentation results.
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
        output_directory
        / "customer_segments_hierarchical.csv"
    )

    features.to_csv(
        output_file,
        index=False
    )

    return output_file


if __name__ == "__main__":

    print(
        "\n===== HIERARCHICAL CUSTOMER SEGMENTATION ====="
    )

    (
        features,
        sample_features,
        cluster_centers,
        scaler
    ) = run_hierarchical_segmentation(
        n_clusters=3,
        sample_size=5000
    )

    print(
        f"\nFinal customers segmented: "
        f"{len(features)}"
    )

    print(
        f"Number of clusters: "
        f"{features['hierarchical_cluster'].nunique()}"
    )

    print(
        "\n===== FINAL CLUSTER DISTRIBUTION ====="
    )

    print(
        features["hierarchical_cluster"]
        .value_counts()
        .sort_index()
    )

    print(
        "\n===== FINAL CLUSTER CHARACTERISTICS ====="
    )

    cluster_summary = (
        features.groupby("hierarchical_cluster")[
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

    # Add business names
    features = add_segment_information(features)

    print("\n===== FINAL BUSINESS SEGMENTS =====")

    segment_summary = (
        features.groupby(
            [
                "hierarchical_cluster",
                "segment_name"
            ]
        )
        .size()
        .reset_index(name="customer_count")
    )

    print(
        segment_summary.to_string(index=False)
    )

    # Save final 93,357-customer output
    output_file = save_hierarchical_results(
        features
    )

    print(
        f"\nResults saved to:\n{output_file}"
    )