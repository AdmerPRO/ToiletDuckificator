from core.messages.builder import build_banner
from settings import APP_NAME, VERSION_TEXT


def build_application_message() -> str:
    return build_banner(APP_NAME, VERSION_TEXT)
