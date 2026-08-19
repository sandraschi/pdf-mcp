"""Local LLM discovery + chat completions (Ollama / LM Studio).

All LLM use is optional and fail-soft: every function returns None / raises
cleanly when no provider is reachable, so non-LLM features never block.
"""

from typing import Any

_OLLAMA = "http://127.0.0.1:11434"
_LM_STUDIO = "http://127.0.0.1:1234"


async def probe(url: str, path: str, timeout: float = 1.5) -> list[dict] | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{url}{path}")
            if r.status_code != 200:
                return None
            data = r.json()
            if "data" in data:
                return data["data"]
            if "models" in data:
                return data["models"]
            return None
    except Exception:
        return None


async def discover_providers() -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    ollama_models = await probe(_OLLAMA, "/api/tags")
    if ollama_models is not None:
        providers["ollama"] = {
            "name": "Ollama",
            "base_url": _OLLAMA,
            "available": True,
            "models": [m.get("name", m.get("model", "")) for m in ollama_models if isinstance(m, dict)],
        }
    else:
        providers["ollama"] = {"name": "Ollama", "base_url": _OLLAMA, "available": False, "models": []}
    lm_models = await probe(_LM_STUDIO, "/v1/models")
    if lm_models is not None:
        providers["lmstudio"] = {
            "name": "LM Studio",
            "base_url": _LM_STUDIO,
            "available": True,
            "models": [m.get("id", "") for m in lm_models if isinstance(m, dict)],
        }
    else:
        providers["lmstudio"] = {"name": "LM Studio", "base_url": _LM_STUDIO, "available": False, "models": []}
    return providers


async def default_provider() -> tuple[str | None, str | None, dict[str, dict[str, Any]]]:
    providers = await discover_providers()
    provider = next((k for k, v in providers.items() if v["available"]), None)
    model = None
    if provider:
        models = providers[provider].get("models") or []
        model = models[0] if models else "llama3"
    return provider, model, providers


async def chat_completion(messages: list[dict], provider: str | None = None, model: str | None = None) -> str:
    """Call a local chat-completion endpoint. Raises on failure."""
    import httpx

    provider, model, providers = await default_provider()
    if not provider or not model:
        raise RuntimeError("No local LLM detected (Ollama 127.0.0.1:11434 or LM Studio 127.0.0.1:1234).")
    base = _OLLAMA if provider == "ollama" else _LM_STUDIO
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{base}/v1/chat/completions",
            json={"model": model, "messages": messages, "stream": False},
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
