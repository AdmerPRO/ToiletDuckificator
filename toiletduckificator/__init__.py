"""ToiletDuckificator package."""

from .obfuscator import ObfuscationOptions, ObfuscationResult, ObfuscatorError, obfuscate_path, obfuscate_source

__all__ = [
    "ObfuscationOptions",
    "ObfuscationResult",
    "ObfuscatorError",
    "obfuscate_path",
    "obfuscate_source",
]
