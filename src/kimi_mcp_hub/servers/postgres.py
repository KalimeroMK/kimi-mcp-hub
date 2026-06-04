"""PostgreSQL MCP server configuration."""

from typing import Any


class PostgreSQLServer:
    """PostgreSQL MCP server — direct SQL queries, schema discovery."""

    name = "postgres"
    display_name = "PostgreSQL"
    description = "Query PostgreSQL databases, read schema, analyze slow queries, generate indexes."
    icon = "🐘"

    @classmethod
    def get_stdio_config(cls, dsn: str) -> dict[str, Any]:
        """STDIO config with database DSN."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", dsn],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "postgres_query", "desc": "Execute SQL query"},
            {"name": "postgres_schema", "desc": "Read database schema"},
            {"name": "postgres_tables", "desc": "List all tables"},
            {"name": "postgres_indexes", "desc": "List indexes for a table"},
            {"name": "postgres_explain", "desc": "EXPLAIN ANALYZE a query"},
            {"name": "postgres_slow_queries", "desc": "Find slow queries from pg_stat_statements"},
        ]
