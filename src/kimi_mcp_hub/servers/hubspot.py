"""HubSpot MCP server configuration."""

from typing import Any


class HubSpotServer:
    """HubSpot MCP server — CRM contacts, companies, deals, engagements."""

    name = "hubspot"
    display_name = "HubSpot"
    description = "CRM operations: contacts, companies, deals, sales analytics."
    icon = "🟠"

    @classmethod
    def get_npx_config(cls, token: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "@shinzolabs/hubspot-mcp"],
            "env": {
                "HUBSPOT_ACCESS_TOKEN": token
            }
        }

    @classmethod
    def get_official_config(cls, token: str) -> dict[str, Any]:
        """Official HubSpot beta MCP server."""
        return {
            "command": "npx",
            "args": ["-y", "@hubspot/mcp-server"],
            "env": {
                "HUBSPOT_API_KEY": token
            }
        }

    @classmethod
    def get_docker_config(cls, token: str) -> dict[str, Any]:
        return {
            "command": "docker",
            "args": [
                "run", "-i", "--rm",
                "-e", f"HUBSPOT_ACCESS_TOKEN={token}",
                "buryhuang/mcp-hubspot:latest"
            ],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "hubspot_list_contacts", "desc": "List contacts"},
            {"name": "hubspot_get_contact", "desc": "Get contact details"},
            {"name": "hubspot_create_contact", "desc": "Create contact"},
            {"name": "hubspot_list_companies", "desc": "List companies"},
            {"name": "hubspot_get_company", "desc": "Get company"},
            {"name": "hubspot_list_deals", "desc": "List deals"},
            {"name": "hubspot_get_deal", "desc": "Get deal"},
            {"name": "hubspot_recent_engagements", "desc": "Recent activity"},
            {"name": "hubspot_search", "desc": "Search CRM"},
        ]
