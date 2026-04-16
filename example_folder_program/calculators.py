from settings import WARNING_THRESHOLD


def summarize_scores(scores: list[int]) -> dict[str, int]:
    total_value = sum(scores)
    high_values = [score for score in scores if score >= WARNING_THRESHOLD]
    return {
        "total": total_value,
        "count": len(scores),
        "high_count": len(high_values),
        "highest": max(scores),
    }
