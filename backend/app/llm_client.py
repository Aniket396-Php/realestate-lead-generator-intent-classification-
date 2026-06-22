"""
Shared LLM client for the PropertyBrix chatbot.
Backend: local Ollama (phi3:latest) via REST API.

The public function `gemini_generate` keeps the same signature as before
so no other file in the project needs to change.

Usage:
    from .llm_client import gemini_generate

    result = await gemini_generate(prompt="Your prompt here", max_tokens=150)
"""

import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env explicitly so this module always finds config regardless of import order
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(_env_path, override=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("LLM_MODEL", "phi3:latest")

# HTTP timeout: generation can be slow on CPU, give it up to 120 s
_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)


async def gemini_generate(
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.5,
) -> str | None:
    """
    Send a prompt to the local Ollama phi3 model and return the text response.
    Function name kept as `gemini_generate` for drop-in compatibility with all
    existing callers (intent_classifier, faq_rag, intent, main).

    Returns None on any failure so callers can use their own fallback logic.
    """
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature":   temperature,
            "num_predict":   max_tokens,   # Ollama's equivalent of max_tokens
        },
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "").strip()
            if not text:
                logger.warning("[Ollama] Empty response from model.")
                return None
            logger.debug(f"[Ollama] Response ({len(text)} chars): {text[:80]}...")
            return text

    except httpx.ConnectError:
        logger.error(
            f"[Ollama] Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
            "Make sure Ollama is running: run `ollama serve` in a terminal."
        )
        return None
    except httpx.TimeoutException:
        logger.error("[Ollama] Request timed out — model may be loading, try again.")
        return None
    except Exception as e:
        logger.error(f"[Ollama] Unexpected error: {e}")
        return None
