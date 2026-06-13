import logging
from collections import Counter

from src.clustering.entropy import calculate_bias_entropy, detect_blindspot
from src.db.articles_repo import get_pending_clusters, save_cluster_metadata

# Placeholder for your primary Gemini completion handler
# Replace this line with your actual system completion function signature!
from src.scoring.gemini_scorer import generate_cluster_title

log = logging.getLogger(__name__)


def run_cluster_labeling_job():
    log.info("Starting cluster metric calculations and labeling...")

    pending = get_pending_clusters()
    if not pending:
        log.info("No un-labeled stories detected.")
        return

    for cluster in pending:
        # 1. Summarize the cluster titles using Gemini
        sample_titles = cluster["titles"][:5]
        try:
            # Assumes generate_cluster_title takes a list of strings and gives back a clean headline string
            generated_title = generate_cluster_title(sample_titles)
        except Exception as e:
            log.error(f"Failed to generate cluster title {cluster['id']}: {e}")
            generated_title = "Breaking Event Profile"

        # 2. Entropy calculations
        biases = cluster["biases"]
        entropy_score = calculate_bias_entropy(biases)
        blindspot = detect_blindspot(entropy_score, biases)

        # 3. Create raw frequency mapping for bias_distribution JSON
        distribution_map = dict(Counter(biases))

        # 4. Save metadata directly to existing columns
        save_cluster_metadata(
            cluster_id=cluster["id"],
            title=generated_title,
            entropy=entropy_score,
            blindspot=blindspot,
            distribution=distribution_map,
        )

        log.info(
            f"Updated Cluster {cluster['id']} -> {generated_title[:40]}... [Entropy: {entropy_score}]"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cluster_labeling_job()
