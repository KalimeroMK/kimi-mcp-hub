---
name: find-skills
description: Discover and install agent skills from the open ecosystem when users need extended capabilities
type: prompt
whenToUse: When the user asks "how do I do X", "can you help with Y", or needs capabilities that may already exist as an installable skill
disableModelInvocation: false
---

# 🔍 find-skills — Discover Agent Skills

## Purpose

When a user needs a capability that may already exist as an installable skill, search the open agent-skills ecosystem instead of reinventing the wheel.

## Workflow

1. **Understand the user's need**
   - Summarize the task or problem in 1–2 sentences.
   - Identify keywords that describe the domain (e.g., "React performance", "database design", "security audit").

2. **Search skills.sh and trusted marketplaces**
   - Query `skills.sh` with relevant keywords.
   - Prefer official and high-reputation sources (`vercel-labs`, `anthropics`, etc.).
   - Consider install counts and recent updates as quality signals.

3. **Evaluate candidates**
   - Read the skill summary and `SKILL.md` when available.
   - Check that the skill matches the user's tool stack (Kimi CLI, Claude Code, etc.).

4. **Recommend and install**
   - Present 1–3 top options with a short rationale.
   - If the user confirms, install the skill using the project's skill manager.
   - Example for Kimi MCP Hub: `kimi-mcp-hub install-skill <skill-name>`

## Guidelines

- Do not write a custom solution if a battle-tested skill already exists.
- Prioritize skills with high install counts and verified publishers.
- Fall back to general problem-solving only when no relevant skill is found.
