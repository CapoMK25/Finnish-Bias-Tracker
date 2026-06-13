import math
from collections import Counter


def calculate_bias_entropy(bias_scores: list[int]) -> float:
    """
    Calculates "Shannon Entropy" for political bias scores (e.g., -2, -1, 0, 1, 2).
    Returns 0.0 if all coverage comes from identical leanings (a complete blindspot).
    """
    if not bias_scores:
        return 0.0

    total_articles = len(bias_scores)
    counts = Counter(bias_scores)

    entropy = 0.0
    for count in counts.values():
        probability = count / total_articles
        entropy -= probability * math.log2(probability)

    return round(entropy, 3)


def detect_blindspot(entropy: float, bias_scores: list[int]) -> str:
    """
    Labels clusters based on programmatic echo chambers using your schema's blindspot_label.
    """
    if not bias_scores:
        return "unknown"

    # An entropy under 0.82 implies heavy dominance by a single side
    if entropy < 0.82:
        dominant_score = Counter(bias_scores).most_common(1)[0][0]
        if dominant_score < 0:
            return "left_skewed_chamber"
        elif dominant_score > 0:
            return "right_skewed_chamber"

    return "balanced"
