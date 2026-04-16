import math


GLOBAL_COUNT = 4


def greet_user(user_name: str) -> str:
    message_text = f"Hello, {user_name}!"
    return message_text


def compute_circle(radius_value: float) -> float:
    area_value = math.pi * radius_value * radius_value
    return area_value + GLOBAL_COUNT


def build_summary(values: list[int]) -> dict[str, int]:
    total_value = sum(values)
    largest_value = max(values)
    indexed_map = {index_number: item_value for index_number, item_value in enumerate(values)}
    return {
        "total": total_value,
        "largest": largest_value,
        "indexed": len(indexed_map),
    }


def make_counter(start_value: int):
    current_value = start_value

    def inner(step_value: int) -> int:
        nonlocal current_value
        current_value += step_value
        return current_value

    return inner


if __name__ == "__main__":
    print(greet_user("Toilet Duck"))
    print(round(compute_circle(3.5), 2))
    print(build_summary([3, 5, 8, 13]))
    counter = make_counter(10)
    print(counter(2))
    print(counter(7))
