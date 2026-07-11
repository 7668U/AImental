import json
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Iterable, Optional
from urllib.parse import urlparse


SENSITIVE_ENV_NAMES = (
    "HEPAI_API_KEY",
    "OPENAI_API_KEY",
    "COS_SECRET_ID",
    "COS_SECRET_KEY",
    "SECRET_KEY",
    "DATA_ENCRYPTION_KEYS",
    "DATA_BLIND_INDEX_KEY",
    "PRIVATE_MEDIA_URL_SIGNING_KEY",
)

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(secret[_-]?key\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
)


class LLMSecurityError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMSecurityConfig:
    allowed_models: frozenset[str]
    allowed_hosts: frozenset[str]
    default_timeout_seconds: float
    max_retries: int
    max_messages: int
    max_message_chars: int
    max_total_message_chars: int
    default_max_tokens: int
    max_output_tokens: int
    max_concurrent_requests: int
    queue_timeout_seconds: float
    allow_streaming: bool


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, *, minimum: Optional[int] = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(value, minimum)
    return value


def env_float(name: str, default: float, *, minimum: Optional[float] = None) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(value, minimum)
    return value


def env_csv(name: str, default_values: Iterable[str]) -> frozenset[str]:
    raw = os.getenv(name)
    if raw is None:
        values = list(default_values)
    else:
        values = [item.strip() for item in raw.split(",")]
    return frozenset(item for item in values if item)


def build_security_config(*, model: str) -> LLMSecurityConfig:
    allowed_models = set(env_csv("LLM_ALLOWED_MODELS", [model]))
    if model:
        allowed_models.add(model)
    return LLMSecurityConfig(
        allowed_models=frozenset(allowed_models),
        allowed_hosts=env_csv("LLM_ALLOWED_HOSTS", ["aiapi.ihep.ac.cn"]),
        default_timeout_seconds=env_float("LLM_DEFAULT_TIMEOUT_SECONDS", 60.0, minimum=1.0),
        max_retries=env_int("LLM_MAX_RETRIES", 1, minimum=0),
        max_messages=env_int("LLM_MAX_MESSAGES", 120, minimum=1),
        max_message_chars=env_int("LLM_MAX_MESSAGE_CHARS", 100_000, minimum=1_000),
        max_total_message_chars=env_int("LLM_MAX_TOTAL_MESSAGE_CHARS", 250_000, minimum=10_000),
        default_max_tokens=env_int("LLM_DEFAULT_MAX_TOKENS", 1500, minimum=1),
        max_output_tokens=env_int("LLM_MAX_OUTPUT_TOKENS", 4096, minimum=1),
        max_concurrent_requests=env_int("LLM_MAX_CONCURRENT_REQUESTS", 8, minimum=1),
        queue_timeout_seconds=env_float("LLM_QUEUE_TIMEOUT_SECONDS", 5.0, minimum=0.0),
        allow_streaming=env_bool("LLM_ALLOW_STREAMING", False),
    )


def configured_secrets(extra: Iterable[str] = ()) -> list[str]:
    secrets: list[str] = []
    for name in SENSITIVE_ENV_NAMES:
        value = os.getenv(name, "").strip()
        if len(value) >= 6:
            secrets.append(value)
    for value in extra:
        if value and len(value) >= 6:
            secrets.append(value)
    return secrets


def redact_secrets(value: object, extra_secrets: Iterable[str] = ()) -> str:
    text = str(value)
    for secret in configured_secrets(extra_secrets):
        text = text.replace(secret, "[redacted]")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}[redacted]" if match.groups() else "[redacted]", text)
    return text


def validate_base_url(base_url: str, allowed_hosts: Iterable[str]) -> None:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    allowed = {item.lower() for item in allowed_hosts if item}
    if parsed.scheme != "https":
        raise LLMSecurityError("LLM base URL must use https.")
    if not host:
        raise LLMSecurityError("LLM base URL host is missing.")
    host_allowed = host in allowed or any(item.startswith(".") and host.endswith(item) for item in allowed)
    if not host_allowed:
        raise LLMSecurityError("LLM base URL host is not in LLM_ALLOWED_HOSTS.")


def _content_length(content: Any) -> int:
    if content is None:
        return 0
    if isinstance(content, str):
        return len(content)
    try:
        return len(json.dumps(content, ensure_ascii=False, separators=(",", ":")))
    except TypeError:
        return len(str(content))


def _validate_messages(messages: Any, config: LLMSecurityConfig) -> None:
    if not isinstance(messages, list):
        raise LLMSecurityError("LLM messages must be a list.")
    if len(messages) > config.max_messages:
        raise LLMSecurityError("LLM message count exceeds the configured limit.")

    total_chars = 0
    for message in messages:
        if not isinstance(message, dict):
            raise LLMSecurityError("Each LLM message must be an object.")
        role = message.get("role")
        if role not in {"system", "developer", "user", "assistant", "tool"}:
            raise LLMSecurityError("LLM message role is not allowed.")
        chars = _content_length(message.get("content"))
        if chars > config.max_message_chars:
            raise LLMSecurityError("A single LLM message exceeds the configured size limit.")
        total_chars += chars
    if total_chars > config.max_total_message_chars:
        raise LLMSecurityError("LLM prompt exceeds the configured total size limit.")


def _sanitized_exception_message(exc: Exception, extra_secrets: Iterable[str]) -> str:
    details = redact_secrets(str(exc), extra_secrets)[:800]
    exc_type = type(exc).__name__
    return f"LLM request failed ({exc_type}): {details}"


class SecureChatCompletions:
    def __init__(self, completions: Any, config: LLMSecurityConfig, semaphore: threading.BoundedSemaphore, secrets: Iterable[str]):
        self._completions = completions
        self._config = config
        self._semaphore = semaphore
        self._secrets = list(secrets)

    def create(self, **kwargs: Any) -> Any:
        model = str(kwargs.get("model") or "")
        if model not in self._config.allowed_models:
            raise LLMSecurityError("Requested LLM model is not allowed.")
        if kwargs.get("stream") and not self._config.allow_streaming:
            raise LLMSecurityError("Streaming LLM responses are disabled for this backend.")

        _validate_messages(kwargs.get("messages"), self._config)

        if "timeout" not in kwargs or kwargs.get("timeout") is None:
            kwargs["timeout"] = self._config.default_timeout_seconds

        token_key = "max_completion_tokens" if "max_completion_tokens" in kwargs else "max_tokens"
        if token_key not in kwargs or kwargs.get(token_key) is None:
            kwargs[token_key] = self._config.default_max_tokens
        else:
            try:
                kwargs[token_key] = min(int(kwargs[token_key]), self._config.max_output_tokens)
            except (TypeError, ValueError):
                raise LLMSecurityError("LLM max token setting is invalid.") from None

        acquired = self._semaphore.acquire(timeout=self._config.queue_timeout_seconds)
        if not acquired:
            raise LLMSecurityError("LLM concurrency limit reached; please retry shortly.")
        try:
            return self._completions.create(**kwargs)
        except LLMSecurityError:
            raise
        except Exception as exc:
            raise RuntimeError(_sanitized_exception_message(exc, self._secrets)) from None
        finally:
            self._semaphore.release()


class SecureChat:
    def __init__(self, chat: Any, config: LLMSecurityConfig, semaphore: threading.BoundedSemaphore, secrets: Iterable[str]):
        self.completions = SecureChatCompletions(chat.completions, config, semaphore, secrets)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.completions, name)


class SecureLLMClient:
    def __init__(
        self,
        client: Any,
        config: LLMSecurityConfig,
        *,
        secrets: Iterable[str] = (),
        semaphore: Optional[threading.BoundedSemaphore] = None,
    ):
        self._client = client
        self._config = config
        self._secrets = list(secrets)
        self._semaphore = semaphore or threading.BoundedSemaphore(config.max_concurrent_requests)
        self.chat = SecureChat(client.chat, config, self._semaphore, self._secrets)

    def with_options(self, **kwargs: Any) -> "SecureLLMClient":
        return SecureLLMClient(
            self._client.with_options(**kwargs),
            self._config,
            secrets=self._secrets,
            semaphore=self._semaphore,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
