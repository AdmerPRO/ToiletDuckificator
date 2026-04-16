from reports import build_full_report
from settings import APP_NAME, SAMPLE_SCORES


def main() -> None:
    report_text = build_full_report(APP_NAME, SAMPLE_SCORES)
    print(report_text)


if __name__ == "__main__":
    main()
