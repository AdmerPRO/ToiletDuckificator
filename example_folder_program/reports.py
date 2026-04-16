import calculators


def build_full_report(app_name: str, scores: list[int]) -> str:
    summary_data = calculators.summarize_scores(scores)
    return (
        f"{app_name}: total={summary_data['total']}, "
        f"count={summary_data['count']}, "
        f"high={summary_data['high_count']}, "
        f"highest={summary_data['highest']}"
    )
