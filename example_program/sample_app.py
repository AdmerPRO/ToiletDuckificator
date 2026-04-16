import statistics


GLOBAL_OFFSET = 7
APP_SETTINGS = {"mode": "demo", "retries": 2, "enabled": 1}
TEAM_MEMBERS = ["Ada", "Bob", "Cy"]


def build_report(scores: list[int]) -> dict[str, object]:
    total_score = sum(scores)
    average_score = round(statistics.mean(scores), 2)
    high_scores = [score for score in scores if score > GLOBAL_OFFSET]
    indexed_scores = {index_value: score_value for index_value, score_value in enumerate(scores)}
    return {
        "total": total_score,
        "average": average_score,
        "high_scores": high_scores,
        "indexed_count": len(indexed_scores),
    }


def make_multiplier(base_value: int):
    current_value = base_value

    def inner(step_value: int) -> int:
        nonlocal current_value
        current_value += step_value
        return current_value * GLOBAL_OFFSET

    return inner


def summarize_team() -> dict[str, object]:
    retry_budget = APP_SETTINGS["retries"] + len(TEAM_MEMBERS)
    return {
        "mode": APP_SETTINGS["mode"],
        "retry_budget": retry_budget,
        "members": TEAM_MEMBERS,
    }


if __name__ == "__main__":
    report = build_report([4, 8, 15, 16, 23, 42])
    multiplier = make_multiplier(3)
    print(report)
    print(summarize_team())
    print(multiplier(2))
    print(multiplier(5))
