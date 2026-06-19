"""Pre-configured MCP server definitions."""

from .jira import JiraServer
from .linear import LinearServer
from .confluence import ConfluenceServer
from .github import GitHubServer
from .slack import SlackServer
from .datadog import DatadogServer
from .figma import FigmaServer
from .figma_context import FigmaContextServer
from .gitlab import GitLabServer
from .gmail import GmailServer
from .hubspot import HubSpotServer
from .grain import GrainServer
from .chrome_devtools import ChromeDevToolsServer
from .postgres import PostgreSQLServer
from .playwright import PlaywrightServer
from .sentry import SentryServer
from .context7 import Context7Server
from .supabase import SupabaseServer
from .perplexity import PerplexityServer
from .stripe import StripeServer
from .desktop_commander import DesktopCommanderServer
from .dbhub import DBHubServer
from .mobile_mcp import MobileMCPServer

__all__ = [
    "JiraServer", "LinearServer", "ConfluenceServer", "GitHubServer",
    "SlackServer", "DatadogServer", "FigmaServer", "FigmaContextServer",
    "GitLabServer", "GmailServer", "HubSpotServer", "GrainServer",
    "ChromeDevToolsServer", "PostgreSQLServer", "PlaywrightServer",
    "SentryServer", "Context7Server", "SupabaseServer", "PerplexityServer",
    "StripeServer", "DesktopCommanderServer", "DBHubServer", "MobileMCPServer",
]
