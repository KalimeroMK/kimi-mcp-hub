"""DBHub MCP server configuration."""

from typing import Any


class DBHubServer:
    """DBHub MCP -- multi-database gateway (PostgreSQL, MySQL, SQLite, SQL Server, MariaDB)."""

    name = "dbhub"
    display_name = "DBHub"
    description = "Multi-database MCP gateway with SQL execution and schema exploration."
    icon = "🗄️"

    @classmethod
    def get_stdio_config(cls, dsn: str, readonly: bool = False) -> dict[str, Any]:
        """Local stdio server using a database DSN."""
        args = ["-y", "@bytebase/dbhub", "--transport", "stdio", "--dsn", dsn]
        if readonly:
            args.append("--readonly")
        return {
            "command": "npx",
            "args": args,
            "env": {},
        }

    @classmethod
    def get_docker_config(cls, dsn: str, readonly: bool = False) -> dict[str, Any]:
        """Docker-based DBHub server."""
        args = [
            "run", "--rm", "-i",
            "bytebase/dbhub",
            "--transport", "stdio",
            "--dsn", dsn,
        ]
        if readonly:
            args.append("--readonly")
        return {
            "command": "docker",
            "args": args,
            "env": {},
        }

    @classmethod
    def get_demo_config(cls) -> dict[str, Any]:
        """Demo DBHub server with built-in sample database."""
        return {
            "command": "npx",
            "args": ["-y", "@bytebase/dbhub", "--transport", "stdio", "--demo"],
            "env": {},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "execute_sql", "desc": "Execute SQL queries with safety controls"},
            {"name": "search_objects", "desc": "Explore schemas, tables, columns, indexes"},
        ]
