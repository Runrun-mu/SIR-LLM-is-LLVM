"""Tests for LLM provider abstraction."""

import pytest
from unittest.mock import MagicMock, patch

from sir.llm.provider import (
    AnthropicProvider,
    LLMResponse,
    OpenAICompatibleProvider,
    create_provider,
    PRESETS,
)


class TestLLMResponse:
    def test_response(self):
        r = LLMResponse(text="hello")
        assert r.text == "hello"


class TestCreateProvider:
    def test_anthropic_default(self):
        with patch("sir.llm.provider.AnthropicProvider.__init__", return_value=None) as mock:
            p = create_provider("anthropic", api_key="sk-test")
            assert isinstance(p, AnthropicProvider)

    def test_openai(self):
        with patch("sir.llm.provider.OpenAICompatibleProvider.__init__", return_value=None):
            p = create_provider("openai", api_key="sk-test")
            assert isinstance(p, OpenAICompatibleProvider)

    def test_deepseek(self):
        with patch("sir.llm.provider.OpenAICompatibleProvider.__init__", return_value=None):
            p = create_provider("deepseek", api_key="sk-test")
            assert isinstance(p, OpenAICompatibleProvider)

    def test_gemini(self):
        with patch("sir.llm.provider.OpenAICompatibleProvider.__init__", return_value=None):
            p = create_provider("gemini", api_key="sk-test")
            assert isinstance(p, OpenAICompatibleProvider)

    def test_custom_provider(self):
        with patch("sir.llm.provider.OpenAICompatibleProvider.__init__", return_value=None):
            p = create_provider("custom", api_key="key", model="my-model", base_url="http://localhost:8000/v1")
            assert isinstance(p, OpenAICompatibleProvider)

    def test_model_override(self):
        with patch("sir.llm.provider.AnthropicProvider.__init__", return_value=None) as mock:
            p = create_provider("anthropic", api_key="sk-test", model="claude-opus-4-6")
            mock.assert_called_once_with(api_key="sk-test", model="claude-opus-4-6")


class TestPresets:
    def test_all_presets_have_three_fields(self):
        for name, preset in PRESETS.items():
            assert len(preset) == 3, f"Preset {name} should have (base_url, model, env_var)"

    def test_known_presets(self):
        assert "anthropic" in PRESETS
        assert "openai" in PRESETS
        assert "deepseek" in PRESETS
        assert "gemini" in PRESETS


class TestAnthropicProviderComplete:
    def test_complete(self):
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.model = "test-model"
        provider.client = MagicMock()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"result": "ok"}')]
        provider.client.messages.create.return_value = mock_response

        result = provider.complete(system="sys", user="usr", max_tokens=100)
        assert result.text == '{"result": "ok"}'
        provider.client.messages.create.assert_called_once_with(
            model="test-model",
            max_tokens=100,
            system="sys",
            messages=[{"role": "user", "content": "usr"}],
        )


class TestOpenAICompatibleProviderComplete:
    def test_complete(self):
        provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
        provider.model = "gpt-4o"
        provider.client = MagicMock()

        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "ok"}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        provider.client.chat.completions.create.return_value = mock_response

        result = provider.complete(system="sys", user="usr", max_tokens=100)
        assert result.text == '{"result": "ok"}'
        provider.client.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            max_tokens=100,
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "usr"},
            ],
        )


class TestIntentParserWithProvider:
    """Test that IntentParser works with the provider abstraction."""

    def test_parse_uses_provider(self):
        from sir.intent.parser import IntentParser
        from sir.ir.schema import Node, NodeKind, Snapshot

        mock_provider = MagicMock()
        mock_provider.complete.return_value = LLMResponse(
            text='{"action": "create", "targets": [{"kind": "module", "name": "Auth"}]}'
        )

        parser = IntentParser(mock_provider)
        snap = Snapshot(nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="Test")])
        result = parser.parse("Add auth module", snap)

        assert result.action.value == "create"
        assert result.targets[0].name == "Auth"
        mock_provider.complete.assert_called_once()


class TestPatchBuilderWithProvider:
    """Test that PatchBuilder works with the provider abstraction."""

    def test_build_uses_provider(self):
        from sir.intent.schema import IntentAction, IntentSpec, IntentTarget
        from sir.ir.schema import Node, NodeKind, Snapshot
        from sir.patch.builder import PatchBuilder

        mock_provider = MagicMock()
        mock_provider.complete.return_value = LLMResponse(
            text='{"description": "add module", "operations": [{"op": "add_node", "value": {"id": "mod_auth", "kind": "module", "name": "Auth"}}]}'
        )

        builder = PatchBuilder(mock_provider)
        snap = Snapshot(nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="Test")])
        intent = IntentSpec(
            action=IntentAction.CREATE,
            targets=[IntentTarget(kind="module", name="Auth")],
        )
        result = builder.build(intent, snap)

        assert result.description == "add module"
        assert len(result.operations) == 1
        mock_provider.complete.assert_called_once()
