"""Desktop Commander MCP server configuration."""

from typing import Any


class DesktopCommanderServer:
    """Desktop Commander MCP -- terminal, file ops, process and diff editing."""

    name = "desktop-commander"
    display_name = "Desktop Commander"
    description = "Terminal commands, file system search, process management, and diff editing."
    icon = "🖥️"

    @classmethod
    def get_stdio_config(cls) -> dict[str, Any]:
        """Local stdio server via npx."""
        return {
            "command": "npx",
            "args": ["-y", "@wonderwhy-er/desktop-commander@latest"],
            "env": {},
        }

    @classmethod
    def get_docker_config(cls) -> dict[str, Any]:
        """Docker-based Desktop Commander server."""
        return {
            "command": "docker",
            "args": ["run", "--rm", "-i", "mcp/desktop-commander:latest"],
            "env": {},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "execute_command", "desc": "Run terminal commands"},
            {"name": "read_output", "desc": "Read output from a running process"},
            {"name": "force_terminate", "desc": "Terminate a running process"},
            {"name": "search_files", "desc": "Search files by name or content"},
            {"name": "edit_file", "desc": "Apply search/replace diff edits"},
            {"name": "list_directory", "desc": "List directory contents"},
            {"name": "read_file", "desc": "Read file contents"},
            {"name": "write_file", "desc": "Write file contents"},
        ]
