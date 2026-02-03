"""
Application configuration module (deprecated).

This module is kept for backward compatibility.
New code should import from app.core.env_config instead.

모든 환경변수 접근은 get_settings() 함수를 통해서만 이루어져야 합니다.
직접 import os; os.environ.get() 사용을 금지합니다.
"""

# Import all symbols from env_config for backward compatibility
from app.core.env_config import (
    Settings,
    get_settings,
    validate_env,
    EnvConfigError,
)

__all__ = [
    "Settings",
    "get_settings",
    "validate_env",
    "EnvConfigError",
]
