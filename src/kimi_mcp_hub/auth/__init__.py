"""OAuth and token management for MCP servers.

Usage:
    from kimi_mcp_hub.auth import authenticate

    # Auto browser open + device flow
    token = authenticate("github")
    token = authenticate("jira")
    token = authenticate("gmail")
"""

from .oauth import (
    OAuthHandler,
    TokenStore,
    DeviceFlowHandler,
    WebFlowHandler,
    LocalCallbackServer,
    generate_pkce_pair,
)
from .providers import authenticate, AUTH_HANDLERS

__all__ = [
    "authenticate",
    "AUTH_HANDLERS",
    "OAuthHandler",
    "TokenStore",
    "DeviceFlowHandler",
    "WebFlowHandler",
    "LocalCallbackServer",
    "generate_pkce_pair",
]
