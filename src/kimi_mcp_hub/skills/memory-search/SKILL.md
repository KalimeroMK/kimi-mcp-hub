---
name: memory-search
description: Token-efficient search of persistent session memory via the kimi-memory MCP tools.
type: prompt
whenToUse: When the user asks about project history, past decisions, earlier bugs or fixes, "what did we do last time", or when answering would otherwise require re-exploring the codebase.
disableModelInvocation: false
---
Search persistent memory before re-exploring. Past sessions already captured the answer — retrieving it costs ~100 tokens, re-deriving it costs thousands.

## The 3-layer rule

Fetch details only after filtering. Never call `memory_get` on ids you have not narrowed down first.

**Layer 1 — `memory_search` (compact index, ~50-100 tokens/result)**
- `query` (required): search terms; punctuation and quotes are safe
- `type`: filter by observation type, e.g. `session` or `tool`
- `project` / `all_projects`: defaults to the current working directory; set `all_projects: true` when the answer may live in another project
- `limit`: default 20, max 100
- Returns only `#id, time, type, title` — no bodies. Start every lookup here.

**Layer 2 — `memory_timeline` (chronological context)**
- `anchor_id` (required): an id from layer 1
- `before` / `after`: neighbours on each side (default 3, max 25)
- Use when a hit needs surrounding context: what led to it, what came after.

**Layer 3 — `memory_get` (full bodies, ~500-1000 tokens each)**
- `ids` (required): batch of integer ids, max 20 per call
- Pass a filtered batch in one call — never one call per id, never unfiltered ids.

## Example session

User: "didn't we hit an authentication bug before?"

```
memory_search(query="authentication bug")
→ 3 match(es):
  #412  2026-09-10 14:22  tool     Fixed token refresh race in auth middleware
  #387  2026-09-08 09:15  session  Debugged 401 loop after deploy
  #355  2026-09-05 17:40  tool     Repro: expired JWT not cleared from cookie

memory_timeline(anchor_id=387, before=2, after=2)
→ shows #385-#389: deploy, 401 reports, root-cause hypothesis, fix, verify

memory_get(ids=[412, 387])
→ full bodies of the two relevant observations only
```

Answer from those two bodies. Total cost: one index scan, one timeline, two full texts — instead of re-reading the auth module.

## When to use `memory_save`

Save a note only when it should survive the session: a decision and its reason, a project convention, a non-obvious gotcha. Notes with the default `category="project"` are injected at the start of future sessions.
- Do NOT save: anything the hooks already capture (tool calls, errors, session flow), transient state, or restatements of the code.
- Do save: "we chose X over Y because Z", "always run migrations with flag F here", "service S silently drops payloads > 64KB".

## When a hook asks for a summary

If a `[Memory]` message asks you to save a summary, call `memory_summarize` once with the `session_id` it gives you: a specific title (under 90 characters) and a short markdown summary -- what was asked, what was done (file paths, and the key content of anything that exists only in chat, such as a draft or an answer), decisions with reasons, and what is still open. Then reply with one short line. Never include secrets; `<private>` spans are dropped.

## Boundaries

Read-only retrieval plus deliberate saves. Memory is project-scoped by default — widen with `all_projects` only when the local search comes up empty. If search and timeline both miss, say so and fall back to exploring the code; do not fetch broad id ranges hoping to stumble on the answer.
