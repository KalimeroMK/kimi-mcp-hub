"""Stripe MCP server configuration."""

from typing import Any


class StripeServer:
    """Stripe MCP server -- official remote (OAuth) or local API key."""

    name = "stripe"
    display_name = "Stripe"
    description = "Manage payments, customers, subscriptions, invoices, and billing."
    icon = "💳"

    # Official Stripe remote MCP endpoint (OAuth 2.1)
    OFFICIAL_URL = "https://mcp.stripe.com"

    @classmethod
    def get_official_config(cls) -> dict[str, Any]:
        """Official Stripe remote MCP server (OAuth 2.1 browser flow)."""
        return {
            "transport": "http",
            "url": cls.OFFICIAL_URL,
            "auth": "oauth",
        }

    @classmethod
    def get_official_stdio_config(cls) -> dict[str, Any]:
        """Official Stripe remote MCP wrapped with mcp-remote for stdio clients."""
        return {
            "command": "npx",
            "args": ["-y", "mcp-remote", cls.OFFICIAL_URL],
            "url": cls.OFFICIAL_URL,
        }

    @classmethod
    def get_stdio_config(cls, api_key: str, tools: str = "all") -> dict[str, Any]:
        """Local Stripe MCP server using a restricted API key."""
        return {
            "command": "npx",
            "args": ["-y", "@stripe/mcp", f"--tools={tools}", f"--api-key={api_key}"],
            "env": {},
        }

    @classmethod
    def get_docker_config(cls, api_key: str, tools: str = "all") -> dict[str, Any]:
        """Docker-based Stripe MCP server using a restricted API key."""
        return {
            "command": "docker",
            "args": [
                "run", "--rm", "-i",
                "mcp/stripe",
                f"--tools={tools}",
                f"--api-key={api_key}",
            ],
            "env": {},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "stripe_create_customer", "desc": "Create a customer"},
            {"name": "stripe_list_customers", "desc": "List customers"},
            {"name": "stripe_create_payment_link", "desc": "Create a payment link"},
            {"name": "stripe_create_invoice", "desc": "Create an invoice"},
            {"name": "stripe_list_invoices", "desc": "List invoices"},
            {"name": "stripe_create_subscription", "desc": "Create a subscription"},
            {"name": "stripe_list_subscriptions", "desc": "List subscriptions"},
            {"name": "stripe_create_refund", "desc": "Create a refund"},
        ]
