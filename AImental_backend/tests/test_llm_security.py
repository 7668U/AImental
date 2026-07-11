import unittest

from llm_security import (
    LLMSecurityConfig,
    LLMSecurityError,
    SecureLLMClient,
    redact_secrets,
    validate_base_url,
)


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"ok": True}


class FakeChat:
    def __init__(self, completions):
        self.completions = completions


class FakeClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = FakeChat(self.completions)

    def with_options(self, **kwargs):
        return self


def test_config() -> LLMSecurityConfig:
    return LLMSecurityConfig(
        allowed_models=frozenset({"safe-model"}),
        allowed_hosts=frozenset({"api.example.com"}),
        default_timeout_seconds=30.0,
        max_retries=0,
        max_messages=4,
        max_message_chars=100,
        max_total_message_chars=200,
        default_max_tokens=16,
        max_output_tokens=32,
        max_concurrent_requests=1,
        queue_timeout_seconds=0.1,
        allow_streaming=False,
    )


class LLMSecurityTestCase(unittest.TestCase):
    def test_redacts_known_secret_shapes(self):
        text = redact_secrets(
            "Authorization: Bearer abc123 api_key=secret-value sk-abcdefghijklmnop",
            ["secret-value"],
        )
        self.assertNotIn("abc123", text)
        self.assertNotIn("secret-value", text)
        self.assertNotIn("sk-abcdefghijklmnop", text)

    def test_validate_base_url_requires_https_allowed_host(self):
        validate_base_url("https://api.example.com/v1", {"api.example.com"})

        with self.assertRaises(LLMSecurityError):
            validate_base_url("http://api.example.com/v1", {"api.example.com"})

        with self.assertRaises(LLMSecurityError):
            validate_base_url("https://evil.example.net/v1", {"api.example.com"})

    def test_secure_client_validates_and_applies_safe_defaults(self):
        fake = FakeClient()
        client = SecureLLMClient(fake, test_config(), secrets=["secret-value"])

        result = client.chat.completions.create(
            model="safe-model",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=1000,
        )

        self.assertEqual(result, {"ok": True})
        call = fake.completions.calls[0]
        self.assertEqual(call["timeout"], 30.0)
        self.assertEqual(call["max_tokens"], 32)

    def test_secure_client_rejects_unexpected_model(self):
        fake = FakeClient()
        client = SecureLLMClient(fake, test_config())

        with self.assertRaises(LLMSecurityError):
            client.chat.completions.create(
                model="unsafe-model",
                messages=[{"role": "user", "content": "hello"}],
            )


if __name__ == "__main__":
    unittest.main()
