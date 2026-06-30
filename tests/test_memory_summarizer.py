"""Tests for memory.summarizer."""

from unittest import mock

import pytest
import requests

from kimi_mcp_hub.memory.summarizer import Summarizer


class TestSummarizer:
    def test_build_prompt_includes_observations(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        observations = [
            {"type": "tool", "summary": "Used bash", "content": "ls -la"},
            {"type": "session", "summary": "Session completed", "content": "Session ended"},
        ]
        prompt = summarizer._build_prompt(observations)
        assert "Used bash" in prompt
        assert "ls -la" in prompt
        assert "Session completed" in prompt

    def test_summarize_success_returns_markdown(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        with mock.patch("kimi_mcp_hub.memory.summarizer.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "## Summary\n\nGreat session."}}]
            }
            mock_post.return_value.status_code = 200
            result = summarizer.summarize_session([{"type": "session", "summary": "done", "content": "done"}])
        assert result == "## Summary\n\nGreat session."

    def test_summarize_missing_api_key_returns_none(self):
        summarizer = Summarizer(api_key="", model="gpt-4o-mini")
        assert summarizer.summarize_session([]) is None

    def test_summarize_api_error_returns_none(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        with mock.patch("kimi_mcp_hub.memory.summarizer.requests.post") as mock_post:
            mock_post.side_effect = Exception("network down")
            assert summarizer.summarize_session([]) is None

    def test_summarize_http_error_returns_none(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        with mock.patch("kimi_mcp_hub.memory.summarizer.requests.post") as mock_post:
            mock_post.side_effect = requests.HTTPError("Unauthorized")
            assert summarizer.summarize_session([]) is None

    def test_summarize_malformed_json_returns_none(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        with mock.patch("kimi_mcp_hub.memory.summarizer.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"error": "invalid"}
            mock_post.return_value.status_code = 200
            assert summarizer.summarize_session([]) is None

    def test_from_config_enabled_returns_configured_summarizer(self):
        config = mock.Mock()
        config.is_memory_summary_enabled.return_value = True
        config.get_memory_summary_api_key.return_value = "sk-enabled"
        config.get_memory_summary_model.return_value = "gpt-4o"
        config.get_memory_summary_base_url.return_value = "https://api.example.com/v1"

        summarizer = Summarizer.from_config(config)

        assert summarizer.api_key == "sk-enabled"
        assert summarizer.model == "gpt-4o"
        assert summarizer.base_url == "https://api.example.com/v1"

    def test_from_config_disabled_returns_empty_summarizer(self):
        config = mock.Mock()
        config.is_memory_summary_enabled.return_value = False

        summarizer = Summarizer.from_config(config)

        assert summarizer.api_key == ""
        assert summarizer.model == ""
        assert summarizer.base_url == ""
