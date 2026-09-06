"""
Centralized Groq AI Client

Purpose:
- Load GROQ_API_KEY from environment
- Load GROQ_MODEL from environment
- Provide one shared Groq client
- Keep AI configuration consistent across the application
- Make testing/mocking easier

Production/UI:
    Uses REAL Groq.

Tests:
    The client can be patched/mocked without changing business logic.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "openai/gpt-oss-20b"


def get_groq_api_key() -> str:
    """
    Return the configured Groq API key.

    Raises:
        RuntimeError: If GROQ_API_KEY is not configured.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. "
            "Add GROQ_API_KEY to your .env file."
        )

    return api_key


def get_groq_model() -> str:
    """
    Return the Groq model configured for the application.

    GROQ_MODEL can be overridden through the environment.
    """

    return os.getenv("GROQ_MODEL", DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Shared Groq Client
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """
    Return a shared Groq client.

    The client is cached so the application does not repeatedly
    instantiate Groq clients during one process.
    """

    return Groq(api_key=get_groq_api_key())


# ---------------------------------------------------------------------------
# Application AI Configuration
# ---------------------------------------------------------------------------

def get_ai_config() -> dict:
    """
    Return the active AI configuration.

    Useful for:
    - UI diagnostics
    - logging
    - debugging
    - health checks
    """

    return {
        "provider": "groq",
        "model": get_groq_model(),
    }


# ---------------------------------------------------------------------------
# Testing / Reset
# ---------------------------------------------------------------------------

def reset_groq_client() -> None:
    """
    Clear the cached Groq client.

    Useful for tests or when environment configuration changes.
    """

    get_groq_client.cache_clear()