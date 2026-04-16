from core.messages.formatters import emphasize_text


def build_banner(app_name: str, version_text: str) -> str:
    return emphasize_text(f"{app_name} running on {version_text}")
