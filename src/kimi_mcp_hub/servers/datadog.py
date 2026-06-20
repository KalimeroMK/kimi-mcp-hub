"""Datadog MCP server configuration."""

from typing import Any


class DatadogServer:
    """Datadog MCP server — official remote HTTP server."""

    name = "datadog"
    display_name = "Datadog"
    description = "Query metrics, search logs, analyze APM traces, manage monitors."
    icon = "🐕"

    OFFICIAL_URL = "https://mcp.datadoghq.com/v1/mcp"

    @classmethod
    def get_official_config(cls, api_key: str, app_key: str) -> dict[str, Any]:
        """Official remote Datadog MCP server.

        Docs: https://docs.datadoghq.com/mcp_server/setup/
        """
        return {
            "transport": "http",
            "url": cls.OFFICIAL_URL,
            "headers": {
                "DD_API_KEY": api_key,
                "DD_APPLICATION_KEY": app_key,
            },
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "datadog_query_metrics", "desc": "Query timeseries metrics"},
            {"name": "datadog_search_logs", "desc": "Search logs with filters"},
            {"name": "datadog_list_monitors", "desc": "List monitors"},
            {"name": "datadog_get_monitor", "desc": "Get monitor details"},
            {"name": "datadog_mute_monitor", "desc": "Mute monitor"},
            {"name": "datadog_list_services", "desc": "APM services"},
            {"name": "datadog_get_traces", "desc": "APM traces"},
            {"name": "datadog_list_dashboards", "desc": "List dashboards"},
            {"name": "datadog_get_dashboard", "desc": "Get dashboard"},
            {"name": "datadog_list_hosts", "desc": "Infrastructure hosts"},
            {"name": "datadog_create_monitor", "desc": "Create monitor"},
            {"name": "datadog_query_events", "desc": "Query events"},
        ]
