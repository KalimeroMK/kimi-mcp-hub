"""Central registry of MCP servers and skills.

Single source of truth for the SERVERS and SKILLS catalogs. The CLI, the
post-install banner, and the version/status displays all derive their counts
from this module, so they can never drift apart.
"""

from __future__ import annotations

from .servers import (
    ChromeDevToolsServer,
    Context7Server,
    ConfluenceServer,
    DatadogServer,
    DBHubServer,
    DesktopCommanderServer,
    FigmaContextServer,
    FigmaServer,
    GitHubServer,
    GitLabServer,
    GmailServer,
    GrainServer,
    HubSpotServer,
    JiraServer,
    LinearServer,
    MobileMCPServer,
    ObsidianServer,
    PerplexityServer,
    PlaywrightServer,
    PostgreSQLServer,
    SentryServer,
    SlackServer,
    StripeServer,
    SupabaseServer,
)

SERVERS = {
    "jira": JiraServer,
    "linear": LinearServer,
    "confluence": ConfluenceServer,
    "github": GitHubServer,
    "slack": SlackServer,
    "datadog": DatadogServer,
    "figma": FigmaServer,
    "figma-context": FigmaContextServer,
    "gitlab": GitLabServer,
    "gmail": GmailServer,
    "hubspot": HubSpotServer,
    "grain": GrainServer,
    "chrome-devtools": ChromeDevToolsServer,
    "postgres": PostgreSQLServer,
    "playwright": PlaywrightServer,
    "sentry": SentryServer,
    "context7": Context7Server,
    "supabase": SupabaseServer,
    "perplexity": PerplexityServer,
    "stripe": StripeServer,
    "desktop-commander": DesktopCommanderServer,
    "dbhub": DBHubServer,
    "mobile": MobileMCPServer,
    "obsidian": ObsidianServer,
}

# Core skills are installed by default
CORE_SKILLS = [
    "karpathy",
    "superpowers",
    "headroom",
    "context-mode",
    "cybersecurity",
    "caveman",
    "kimi-mcp-hub-status",
]

# Frontend skills are installed together as a recommended frontend stack
FRONTEND_SKILLS = [
    "react-coder",
    "ts-coder",
    "ui-engineer",
    "ui-ux-pro-max",
    "vercel-react-best-practices",
    "web-design-guidelines",
    "agent-browser",
]

# Servers that are installed automatically during `init` if npx is available
# (no API key required, broadly useful, low risk)
AUTO_INSTALL_SERVERS = ["chrome-devtools", "context7", "playwright"]

# Optional skills are presented in category groups during `init`
OPTIONAL_SKILL_GROUPS = [
    (
        "Code Quality & Review",
        [
            "code-reviewer",
            "code-review",
            "surgical-refactoring",
            "tdd",
            "perf-optimization",
            "security-audit",
            "security-guidance",
            "caveman-review",
        ],
    ),
    (
        "Architecture & Design",
        [
            "api-designer",
            "backend-architect",
            "backend-typescript-architect",
            "codebase-design",
            "domain-modeling",
            "database-expert",
            "api-design",
            "design-system",
        ],
    ),
    (
        "DevOps & Deployment",
        [
            "docker-pro",
            "gitnexus",
            "resolving-merge-conflicts",
            "deployment-patterns",
            "caveman-commit",
        ],
    ),
    (
        "Language / Framework",
        [
            "python-engineer",
            "laravel-engineer",
            "php-pro",
            "wp-plugin-development",
            "react-coder",
            "ts-coder",
            "ui-engineer",
            "ui-ux-pro-max",
        ],
    ),
    ("Data & Migrations", ["database-migrations"]),
    (
        "Testing & Browser",
        [
            "playwright-best-practices",
            "chrome-devtools-skill",
        ],
    ),
    (
        "Research & Automation",
        [
            "search-first",
            "regex-vs-llm-structured-text",
        ],
    ),
    (
        "Productivity & Meta",
        [
            "memory-palace",
            "hindsight",
            "task-master",
            "ralph",
            "grill-me",
            "visual-explainer",
            "research-mode",
            "ecc",
            "skill-creator",
            "agent-automation-recommender",
            "find-skills",
            "claude-compat",
        ],
    ),
    ("Integration", ["stripe-best-practices"]),
]

SKILLS = {
    # ---- Core skills ----
    "karpathy": "Clean, simple, readable code discipline",
    "superpowers": "14 agentic workflows (plan, debug, test, deploy...)",
    "headroom": "Compress large tool outputs to save tokens",
    "context-mode": "Context window optimization and token budget",
    "cybersecurity": "Cybersecurity expert (OWASP, cloud, IR, pentest)",
    "kimi-mcp-hub-status": "Show MCP Hub version and status",
    # ---- Frontend skills ----
    "react-coder": "React 19 specialist (RSC, hooks)",
    "ts-coder": "TypeScript specialist (strict, generics)",
    "ui-engineer": "UI component implementation (Tailwind, a11y)",
    "ui-ux-pro-max": "UI/UX design intelligence and design systems",
    "design-system": "Design tokens, component specs, and systematic design systems",
    "vercel-react-best-practices": "React/Next.js performance optimization",
    "web-design-guidelines": "Audit UI code against Vercel guidelines",
    "agent-browser": "Browser automation for web tasks and testing",
    # ---- Optional skills ----
    "caveman": "Ultra-compressed caveman communication mode",
    "caveman-review": "Ultra-compressed code review comments",
    "caveman-commit": "Ultra-compressed Conventional Commits messages",
    "ecc": "Engineering competence (perf, security, research)",
    "visual-explainer": "HTML diagrams and slides",
    "task-master": "Task management system",
    "gitnexus": "Code knowledge graph and blast radius",
    "ralph": "Autonomous loop with stop-hooks",
    "security-audit": "Security review checklist",
    "security-guidance": "3-layer security scanning guidance",
    "research-mode": "Research-driven development",
    "perf-optimization": "Performance profiling and optimization",
    "memory-palace": "Advanced memory and context retrieval",
    "code-reviewer": "Quick single-agent code review",
    "code-review": "Multi-agent code review (explore/coder/plan)",
    "api-designer": "REST/GraphQL API design",
    "docker-pro": "Docker and Kubernetes best practices",
    "database-expert": "Database design and optimization",
    "backend-architect": "Backend architecture and system design",
    "backend-typescript-architect": "TypeScript/Bun backend architecture",
    "python-engineer": "Python specialist (FastAPI, Django, async)",
    "laravel-engineer": "Laravel specialist (Eloquent, Blade, Livewire)",
    "php-pro": "Senior PHP development (strict typing, Laravel/Symfony, PSR)",
    "wp-plugin-development": "WordPress plugin development with hooks and Settings API",
    "hindsight": "Memory that learns from past decisions",
    "find-skills": "Discover and install agent skills",
    "surgical-refactoring": "Surgical code refactoring without behavior change",
    "stripe-best-practices": "Stripe integration best practices",
    "chrome-devtools-skill": "Chrome DevTools MCP debugging and automation",
    "playwright-best-practices": "Playwright testing best practices",
    "skill-creator": "Create and optimize agent skills",
    "agent-automation-recommender": "Recommend agent automations for codebases",
    "tdd": "Test-driven development with red-green-refactor",
    "codebase-design": "Design deep modules and testable interfaces",
    "domain-modeling": "Build domain models and ubiquitous language",
    "grill-me": "Stress-test a plan or design",
    "resolving-merge-conflicts": "Resolve git merge/rebase conflicts",
    "search-first": "Research-before-coding workflow",
    "database-migrations": "Safe database migration patterns",
    "api-design": "REST API design patterns",
    "deployment-patterns": "CI/CD and deployment best practices",
    "regex-vs-llm-structured-text": "Regex vs LLM parsing decision framework",
    "claude-compat": "Auto-load CLAUDE.md and CLAUDE.local.md at session start",
}
