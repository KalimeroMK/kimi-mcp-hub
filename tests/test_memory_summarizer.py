"""Tests for memory.summarizer."""

from unittest import mock

import pytest
import requests

from kimi_mcp_hub.config import KimiConfig
from kimi_mcp_hub.memory.summarizer import MODES, Summarizer


class TestSummarizer:
    def test_build_prompt_includes_observations(self):
        summarizer = Summarizer(api_key="sk-test", model="gpt-4o-mini")
        observations = [
            {"type": "tool", "summary": "Used bash", "content": "ls -la"},
            {
                "type": "session",
                "summary": "Session completed",
                "content": "Session ended",
            },
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
            result = summarizer.summarize_session(
                [{"type": "session", "summary": "done", "content": "done"}]
            )
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


class TestRequestShape:
    """The request the checker sends must match the one summaries use."""

    def _capture(self, summarizer, monkeypatch):
        sent = {}

        class Response:
            status_code = 200
            ok = True
            text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "Title: did a thing"}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            sent["url"] = url
            sent["body"] = json
            return Response()

        monkeypatch.setattr("kimi_mcp_hub.memory.summarizer.requests.post", fake_post)
        return sent

    def test_temperature_is_omitted_by_default(self, monkeypatch):
        """Kimi's coding models reject any explicit temperature with a 400."""
        s = Summarizer("k", "m", "https://x/v1")
        sent = self._capture(s, monkeypatch)
        s.summarize_session([{"type": "tool", "summary": "Used Bash"}])
        assert "temperature" not in sent["body"]

    def test_temperature_is_sent_when_configured(self, monkeypatch):
        s = Summarizer("k", "m", "https://x/v1", temperature=0.3)
        sent = self._capture(s, monkeypatch)
        s.summarize_session([{"type": "tool", "summary": "Used Bash"}])
        assert sent["body"]["temperature"] == 0.3

    def test_check_uses_the_same_message_shape_as_a_summary(self, monkeypatch):
        """A checker that sends a different shape can pass while summaries fail."""
        s = Summarizer("k", "m", "https://x/v1", temperature=0.3)
        sent = self._capture(s, monkeypatch)
        s.check()
        check_body = dict(sent["body"])

        s.summarize_session([{"type": "tool", "summary": "Used Bash"}])
        summary_body = sent["body"]

        assert [m["role"] for m in check_body["messages"]] == [
            m["role"] for m in summary_body["messages"]
        ]
        assert check_body["temperature"] == summary_body["temperature"]
        assert check_body["model"] == summary_body["model"]

    def test_check_reports_a_rejected_key(self, monkeypatch):
        class Response:
            status_code = 401
            ok = False
            text = "Invalid Authentication"

        monkeypatch.setattr(
            "kimi_mcp_hub.memory.summarizer.requests.post",
            lambda *a, **k: Response(),
        )
        ok, detail = Summarizer("k", "m", "https://x/v1").check()
        assert ok is False
        assert "401" in detail

    def test_check_reports_a_rejected_parameter(self, monkeypatch):
        """This is the failure that silently emptied 1,815 sessions."""

        class Response:
            status_code = 400
            ok = False
            text = '{"error": {"message": "invalid temperature: only 1 is allowed"}}'

        monkeypatch.setattr(
            "kimi_mcp_hub.memory.summarizer.requests.post",
            lambda *a, **k: Response(),
        )
        ok, detail = Summarizer("k", "m", "https://x/v1", temperature=0.3).check()
        assert ok is False
        assert "invalid temperature" in detail

    def test_check_without_a_key(self):
        ok, detail = Summarizer("", "m", "https://x/v1").check()
        assert ok is False
        assert "no API key" in detail


class TestSummaryModes:
    _MARKERS = {
        "code": "Key decisions",
        "chill": "Key outcomes",
        "investigation": "Hypotheses tried",
    }

    def _capture(self, summarizer, monkeypatch):
        sent = {}

        class Response:
            status_code = 200
            ok = True
            text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "Title: did a thing"}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            sent["body"] = json
            return Response()

        monkeypatch.setattr("kimi_mcp_hub.memory.summarizer.requests.post", fake_post)
        return sent

    def test_default_mode_is_code(self):
        assert Summarizer("k", "m", "https://x/v1").mode == "code"

    def test_each_mode_selects_its_prompt(self, monkeypatch):
        for mode, marker in self._MARKERS.items():
            s = Summarizer("k", "m", "https://x/v1", mode=mode)
            sent = self._capture(s, monkeypatch)
            s.summarize_session([{"type": "tool", "summary": "Used Bash"}])
            messages = sent["body"]["messages"]
            assert messages[0]["content"] == MODES[mode]["system"]
            assert marker in messages[1]["content"]

    def test_unknown_mode_falls_back_to_code(self, monkeypatch):
        s = Summarizer("k", "m", "https://x/v1", mode="banana")
        assert s.mode == "code"
        sent = self._capture(s, monkeypatch)
        s.summarize_session([{"type": "tool", "summary": "Used Bash"}])
        messages = sent["body"]["messages"]
        assert messages[0]["content"] == MODES["code"]["system"]
        assert "Key decisions" in messages[1]["content"]

    def test_from_config_passes_mode_through(self):
        config = mock.Mock()
        config.is_memory_summary_enabled.return_value = True
        config.get_memory_summary_mode.return_value = "investigation"
        config.get_memory_summary_base_url.return_value = "https://api.example.com/v1"

        summarizer = Summarizer.from_config(config)

        assert summarizer.mode == "investigation"


class TestSummaryModeConfig:
    def _temp_config(self, tmp_path):
        config = KimiConfig()
        config.config_toml = tmp_path / "config.toml"
        return config

    def test_default_mode_is_code(self, tmp_path, monkeypatch):
        monkeypatch.delenv("KIMI_MEMORY_SUMMARY_MODE", raising=False)
        assert self._temp_config(tmp_path).get_memory_summary_mode() == "code"

    def test_config_toml_sets_mode(self, tmp_path, monkeypatch):
        monkeypatch.delenv("KIMI_MEMORY_SUMMARY_MODE", raising=False)
        config = self._temp_config(tmp_path)
        config.save_toml_config({"memory": {"summary_mode": "chill"}})
        assert config.get_memory_summary_mode() == "chill"

    def test_env_var_overrides_config(self, tmp_path, monkeypatch):
        config = self._temp_config(tmp_path)
        config.save_toml_config({"memory": {"summary_mode": "chill"}})
        monkeypatch.setenv("KIMI_MEMORY_SUMMARY_MODE", "investigation")
        assert config.get_memory_summary_mode() == "investigation"


class TestLocalModel:
    """A local server needs no key, so summaries work with nothing external."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:11434/v1",
            "http://127.0.0.1:1234/v1",
            "http://[::1]:8080/v1",
        ],
    )
    def test_local_urls_are_recognised(self, url):
        assert Summarizer("", "llama3", url).is_local

    def test_remote_url_is_not_local(self):
        assert not Summarizer("", "gpt-4o-mini", "https://api.openai.com/v1").is_local

    def test_keyless_local_summary_is_generated_without_auth_header(self, monkeypatch):
        seen = {}

        class Response:
            ok = True
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "Title: Local"}}]}

        def fake_post(url, headers, json, timeout):
            seen["headers"] = headers
            return Response()

        monkeypatch.setattr("kimi_mcp_hub.memory.summarizer.requests.post", fake_post)
        summarizer = Summarizer("", "llama3", "http://localhost:11434/v1")
        assert summarizer.summarize_session([{"type": "user", "content": "hi"}]) == (
            "Title: Local"
        )
        assert "Authorization" not in seen["headers"]

    def test_keyless_remote_is_still_refused(self):
        assert (
            Summarizer("", "m", "https://api.openai.com/v1").summarize_session([])
            is None
        )
