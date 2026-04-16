"""ToiletDuckificator package."""

from .obfuscator import ObfuscationResult, ObfuscatorError, obfuscate_path, obfuscate_source

__all__ = [
    "ObfuscationResult",
    "ObfuscatorError",
    "obfuscate_path",
    "obfuscate_source",
]
