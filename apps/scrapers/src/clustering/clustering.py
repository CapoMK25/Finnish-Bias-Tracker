"""Core background job that handles vector aggregation,
runs density-based clustering, and filters out noise."""

import logging
import uuid

import numpy as np
from sklearn.cluster import HDBSCAN

from src.db.articles_repo import get_recent_embeddings, update_cluster_assignments

log = logging.getLogger(__name__)


def run_clustering_job():
    log.info("Starting rolling 48h clustering job...")

    # 1. Retrieve the rolling 48-hour data window

    articles = get_recent_embeddings(hours=48)

    if len(articles) < 3:
        log.warning(
            f"Not enough articles with embeddings to cluster ({len(articles)} found). Skipping."
        )

        return

    # 2. Extract IDs and build feature matrix

    article_ids = [a["id"] for a in articles]

    embeddings = np.array([a["embedding"] for a in articles])

    # 3. Initialize HDBSCAN

    # min_cluster_size=2: At least 2 similar articles are required to form a new cluster

    # metric='cosine': Fits our pgvector indexing strategy

    clusterer = HDBSCAN(min_cluster_size=2, metric="cosine", min_samples=1)

    labels = clusterer.fit_predict(embeddings)

    # 4. Map numerical labels to database UUIDs

    generated_cluster_map = {}

    assignments = {}

    for idx, label in enumerate(labels):
        article_id = article_ids[idx]

        if label == -1:
            # -1 signifies noise out-liers: isolate them from any group cluster

            assignments[article_id] = None

        else:
            if label not in generated_cluster_map:
                generated_cluster_map[label] = uuid.uuid4()

            assignments[article_id] = generated_cluster_map[label]

    # 5. Save changes to Postgres

    new_cluster_uuids = list(generated_cluster_map.values())

    update_cluster_assignments(assignments, new_cluster_uuids)

    log.info(
        "clustering_job_complete",
        extra={
            "total_processed": len(articles),
            "clusters_created": len(new_cluster_uuids),
            "noise_count": list(labels).count(-1),
        },
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    run_clustering_job()
