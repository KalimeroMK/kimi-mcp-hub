"""Local web viewer for the persistent memory database.

Runs a small read-only HTTP server on localhost so memory can be browsed in a
browser instead of only through the CLI. Built on the standard library so the
package keeps its zero-dependency install.

Security posture: the database contains raw tool output, which can include
secrets. The server therefore binds to the loopback interface only, rejects
requests whose ``Host`` header is not localhost (which defeats DNS rebinding),
requires a per-run token on every API call, and sends no CORS headers, so a
web page from another origin cannot read the responses.
"""

from __future__ import annotations

import errno
import http.server
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import platformdirs

from .db import MemoryDB

_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}
MAX_PAGE_SIZE = 200
DEFAULT_PORT = 8765


def state_dir() -> Path:
    """Directory holding the viewer's token, pidfile, and log."""
    return Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))


def token_path() -> Path:
    return state_dir() / "viewer-token"


def pid_path() -> Path:
    return state_dir() / "viewer.pid"


def log_path() -> Path:
    return state_dir() / "viewer.log"


def load_or_create_token() -> str:
    """Return the persistent access token, creating it on first use.

    A stable token is what makes the viewer's URL bookmarkable, which an
    always-on service needs. It is stored 0600: anything able to read it could
    already read the database file next to it, so this adds no exposure beyond
    what the database itself has. Use :func:`rotate_token` to invalidate links.
    """
    path = token_path()
    if path.exists():
        existing = path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    return rotate_token()


def rotate_token() -> str:
    """Generate a new token, invalidating every previously shared link."""
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    # Opened directly with 0600 so the secret is never briefly world-readable.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(token)
    return token


def viewer_url(port: int, token: str | None = None) -> str:
    return f"http://127.0.0.1:{port}/?token={token or load_or_create_token()}"


def _is_local_host_header(host_header: str) -> bool:
    """Return True if the Host header points at loopback."""
    if not host_header:
        return False
    host = (
        host_header.rsplit(":", 1)[0]
        if not host_header.startswith("[")
        else (host_header.split("]")[0] + "]")
    )
    return host in _ALLOWED_HOSTS


class MemoryViewerHandler(http.server.BaseHTTPRequestHandler):
    """Read-only HTTP handler backed by :class:`MemoryDB`."""

    server_version = "KimiMemoryViewer/1.0"
    db: MemoryDB
    token: str
    quiet: bool = True

    # ---- plumbing ----------------------------------------------------

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        if not self.quiet:
            super().log_message(fmt, *args)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Memory content must never be embedded or read by another origin.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status=status)

    # ---- routing -----------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if not _is_local_host_header(self.headers.get("Host", "")):
            self._error(403, "non-local Host header rejected")
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        route = parsed.path.rstrip("/") or "/"

        if route == "/":
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        if not route.startswith("/api/"):
            self._error(404, "not found")
            return

        if not secrets.compare_digest(_first(params, "token"), self.token):
            self._error(401, "missing or invalid token")
            return

        try:
            self._handle_api(route, params)
        except ValueError as exc:
            self._error(400, str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            self._error(500, f"internal error: {exc}")

    def _handle_api(self, route: str, params: dict[str, list[str]]) -> None:
        if route == "/api/stats":
            self._json(
                {
                    "observations": self.db.get_stats(),
                    "memories": self.db.get_memory_stats(),
                    "projects": self.db.list_projects(),
                    "types": self.db.list_types(),
                }
            )
            return

        if route == "/api/observations":
            query = _first(params, "q").strip()
            project = _first(params, "project") or None
            obs_type = _first(params, "type") or None
            limit = _int(params, "limit", 50, MAX_PAGE_SIZE)
            offset = _int(params, "offset", 0, 10_000_000)

            if query:
                # Relevance-ordered results have no stable offset, so the
                # client must not offer paging over them.
                rows = self.db.search(
                    query, limit=limit, project_path=project, obs_type=obs_type
                )
                self._json({"rows": rows, "total": len(rows), "paginated": False})
            else:
                rows, total = self.db.browse_observations(
                    limit=limit,
                    offset=offset,
                    project_path=project,
                    obs_type=obs_type,
                )
                self._json({"rows": rows, "total": total, "paginated": True})
            return

        if route.startswith("/api/observations/"):
            raw_id = route.rsplit("/", 1)[-1]
            if not raw_id.isdigit():
                raise ValueError("observation id must be an integer")
            rows = self.db.get_observations_by_ids([int(raw_id)])
            if not rows:
                self._error(404, "observation not found")
                return
            self._json(rows[0])
            return

        if route == "/api/memories":
            query = _first(params, "q").strip()
            project = _first(params, "project") or None
            limit = _int(params, "limit", 50, MAX_PAGE_SIZE)
            rows = (
                self.db.search_memories(query, limit=limit, project_path=project)
                if query
                else self.db.get_memories(limit=limit, project_path=project)
            )
            self._json({"rows": rows, "total": len(rows), "paginated": False})
            return

        self._error(404, "unknown endpoint")


def _first(params: dict[str, list[str]], key: str) -> str:
    values = params.get(key)
    return values[0] if values else ""


def _int(params: dict[str, list[str]], key: str, default: int, maximum: int) -> int:
    raw = _first(params, key)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if value < 0:
        raise ValueError(f"{key} must be non-negative")
    return min(value, maximum)


def build_server(
    db_path: Path | None = None,
    port: int = DEFAULT_PORT,
    token: str | None = None,
) -> tuple[http.server.ThreadingHTTPServer, str]:
    """Create the viewer server bound to loopback. Returns (server, token)."""
    access_token = token or load_or_create_token()

    handler = type(
        "BoundMemoryViewerHandler",
        (MemoryViewerHandler,),
        {"db": MemoryDB(db_path=db_path), "token": access_token},
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    return server, access_token


def has_display() -> bool:
    """Return False when there is clearly no GUI to open a browser in.

    Headless Linux -- a server over SSH, a container, a CI runner -- is the
    common case where auto-open cannot work. Detecting it up front lets the
    caller say so instead of leaving the user waiting for a window that will
    never appear. An explicit ``BROWSER`` is honoured because it may point at a
    working launcher (``wslview`` under WSL, for instance) with no display set.
    """
    if os.environ.get("BROWSER"):
        return True
    if sys.platform.startswith(("linux", "freebsd", "openbsd", "netbsd")):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def open_in_browser(url: str) -> tuple[bool, str]:
    """Try to open ``url``. Returns (opened, reason-when-not-opened)."""
    if not has_display():
        return False, "no graphical display detected"
    try:
        if webbrowser.open(url):
            return True, ""
        return False, "no browser could be launched"
    except webbrowser.Error as exc:
        return False, str(exc)


def _pid_alive(pid: int) -> bool:
    """Return True if a process with this pid exists and we may signal it."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as exc:
        # EPERM means it exists but belongs to someone else.
        return exc.errno == errno.EPERM
    return True


def _reap(pid: int) -> None:
    """Clear a terminated child so it stops showing up as a live process.

    A daemon started from a still-running parent becomes a zombie when it
    exits: the pid remains signalable, so a liveness check would keep
    reporting it as running. Harmless for the CLI, whose process exits
    immediately, but it matters for any caller that outlives the daemon.
    """
    if os.name == "nt":  # pragma: no cover - no zombies on Windows
        return
    try:
        os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, OSError):
        # Not our child, or already reaped -- both fine.
        pass


def _port_accepts(port: int, timeout: float = 0.35) -> bool:
    """Return True if something is listening on the loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def read_pidfile() -> dict | None:
    """Return the recorded daemon state, or None when absent or unreadable."""
    path = pid_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or "pid" not in data:
        return None
    return data


def viewer_status() -> dict:
    """Describe the background viewer: running, stale, or stopped.

    ``stale`` means a pidfile survived a process that is gone -- after a crash
    or a reboot -- so callers can clean up instead of reporting a live server.
    """
    record = read_pidfile()
    if record is None:
        return {"state": "stopped"}

    pid = int(record.get("pid", 0))
    port = int(record.get("port", DEFAULT_PORT))
    if not _pid_alive(pid):
        return {"state": "stale", "pid": pid, "port": port}
    return {
        "state": "running",
        "pid": pid,
        "port": port,
        "responding": _port_accepts(port),
        "url": viewer_url(port),
    }


def _write_pidfile(pid: int, port: int) -> None:
    path = pid_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": pid, "port": port}), encoding="utf-8")


def clear_pidfile() -> None:
    pid_path().unlink(missing_ok=True)


def start_daemon(port: int = DEFAULT_PORT) -> dict:
    """Start the viewer detached from this process, unless it already runs.

    Returns a status dict. This is called from the SessionStart hook, so it
    must return promptly and never raise: a failure to start the viewer is not
    a reason to fail a Kimi session.
    """
    status = viewer_status()
    if status["state"] == "running":
        return {**status, "started": False}
    if status["state"] == "stale":
        clear_pidfile()

    if _port_accepts(port):
        # Something else owns the port; do not fight it or claim it as ours.
        return {"state": "port_busy", "port": port, "started": False}

    command = [
        sys.executable,
        "-m",
        "kimi_mcp_hub",
        "memory",
        "viewer",
        "--no-open",
        "--port",
        str(port),
    ]
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL}
    if os.name == "nt":  # pragma: no cover - exercised on Windows only
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008
    else:
        # New session, so closing the terminal or Ctrl+C does not take it down.
        kwargs["start_new_session"] = True

    try:
        log_path().parent.mkdir(parents=True, exist_ok=True)
        with open(log_path(), "a", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=log, stderr=log, **kwargs)
    except OSError as exc:
        return {"state": "failed", "reason": str(exc), "started": False}

    _write_pidfile(process.pid, port)
    return {
        "state": "running",
        "pid": process.pid,
        "port": port,
        "url": viewer_url(port),
        "started": True,
    }


def stop_daemon(timeout: float = 5.0) -> dict:
    """Stop the background viewer if it is running."""
    status = viewer_status()
    if status["state"] == "stopped":
        return {"state": "stopped", "stopped": False}
    if status["state"] == "stale":
        clear_pidfile()
        return {"state": "stopped", "stopped": False, "cleaned_stale": True}

    pid = status["pid"]
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        clear_pidfile()
        return {"state": "stopped", "stopped": False, "reason": str(exc)}

    sleeper = threading.Event()
    waited = 0.0
    while waited < timeout and _pid_alive(pid):
        _reap(pid)
        sleeper.wait(0.1)
        waited += 0.1

    if _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        _reap(pid)

    clear_pidfile()
    return {"state": "stopped", "stopped": True, "pid": pid}


def serve(
    db_path: Path | None = None,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
    on_ready=None,
    on_open_failed=None,
) -> None:
    """Run the viewer until interrupted."""
    server, token = build_server(db_path=db_path, port=port)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/?token={token}"

    if on_ready is not None:
        on_ready(url)

    if open_browser:

        def launch() -> None:
            opened, reason = open_in_browser(url)
            if not opened and on_open_failed is not None:
                on_open_failed(reason)

        threading.Timer(0.4, launch).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>Kimi Memory</title>
<!-- Inline so the browser never issues a /favicon.ico request the server would 404. -->
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ctext y='13' font-size='13'%3E%F0%9F%A7%A0%3C/text%3E%3C/svg%3E">
<style>
  :root {
    color-scheme: light dark;
    --bg: #ffffff; --panel: #f6f7f9; --border: #dfe3e8;
    --fg: #1c1f23; --muted: #6b7280; --accent: #2f6feb;
    --chip: #e8ecf3;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14161a; --panel: #1b1e24; --border: #2b3038;
      --fg: #e6e8eb; --muted: #9aa4b2; --accent: #5b8cff;
      --chip: #262b33;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--fg);
    font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  header {
    display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
    padding: 12px 16px; border-bottom: 1px solid var(--border); background: var(--panel);
    position: sticky; top: 0; z-index: 5;
  }
  h1 { font-size: 15px; margin: 0 8px 0 0; font-weight: 650; }
  input, select, button {
    font: inherit; color: inherit; background: var(--bg);
    border: 1px solid var(--border); border-radius: 6px; padding: 6px 9px;
  }
  input[type=search] { min-width: 260px; flex: 1 1 260px; }
  button { cursor: pointer; }
  button:hover { border-color: var(--accent); }
  .tabs { display: flex; gap: 6px; }
  .tab.active { border-color: var(--accent); color: var(--accent); }
  main { display: grid; grid-template-columns: minmax(320px, 2fr) 3fr; gap: 0; height: calc(100vh - 57px); }
  @media (max-width: 860px) { main { grid-template-columns: 1fr; } #detail { display: none; } }
  #list { overflow-y: auto; border-right: 1px solid var(--border); }
  #detail { overflow-y: auto; padding: 18px 20px; }
  .row {
    padding: 10px 14px; border-bottom: 1px solid var(--border); cursor: pointer;
  }
  .row:hover { background: var(--panel); }
  .row.sel { background: var(--panel); box-shadow: inset 3px 0 0 var(--accent); }
  .meta { color: var(--muted); font-size: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
  .chip {
    background: var(--chip); border-radius: 999px; padding: 1px 8px; font-size: 11px;
  }
  .title { margin-top: 3px; overflow-wrap: anywhere; }
  pre {
    white-space: pre-wrap; overflow-wrap: anywhere; background: var(--panel);
    border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin: 12px 0 0;
  }
  .empty, .status { padding: 24px 16px; color: var(--muted); }
  .empty code {
    background: var(--chip); border-radius: 4px; padding: 1px 5px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
  }
  .pager { display: flex; gap: 8px; align-items: center; padding: 12px 14px; }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0; }
  dt { color: var(--muted); }
  dd { margin: 0; overflow-wrap: anywhere; }
</style>
</head>
<body>
<header>
  <h1>Kimi Memory</h1>
  <div class="tabs">
    <button class="tab active" data-tab="observations">Observations</button>
    <button class="tab" data-tab="memories">Notes</button>
  </div>
  <input type="search" id="q" placeholder="Search (full-text)…">
  <select id="project"><option value="">All projects</option></select>
  <select id="type"><option value="">All types</option></select>
  <button id="reload">Reload</button>
  <span class="meta" id="stats"></span>
</header>
<main>
  <div id="list"><div class="status">Loading…</div></div>
  <div id="detail"><div class="empty">Select an entry to see the full content.</div></div>
</main>
<script>
const token = new URLSearchParams(location.search).get('token') || '';
const el = (id) => document.getElementById(id);
let tab = 'observations';
let offset = 0;
let rows = [];
let selected = null;

const api = async (path, params = {}) => {
  const qs = new URLSearchParams({ ...params, token });
  const res = await fetch(`${path}?${qs}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || res.statusText);
  }
  return res.json();
};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
));

const shortTime = (t) => (t || '').replace('T', ' ').slice(0, 16);
const shortPath = (p) => (p ? p.split('/').slice(-2).join('/') : '');

function renderList(data) {
  rows = data.rows || [];
  if (!rows.length) {
    el('list').innerHTML = '<div class="empty">Nothing here yet.</div>';
    return;
  }
  const items = rows.map((r) => {
    const title = r.summary || (r.content || '').slice(0, 120) || '(no summary)';
    const chips = [r.type || r.category, shortPath(r.project_path)]
      .filter(Boolean)
      .map((c) => `<span class="chip">${esc(c)}</span>`)
      .join('');
    return `<div class="row" data-id="${r.id}">
      <div class="meta">#${r.id} <span>${esc(shortTime(r.timestamp))}</span> ${chips}</div>
      <div class="title">${esc(title)}</div>
    </div>`;
  }).join('');

  const pager = data.paginated ? `<div class="pager">
      <button id="prev" ${offset === 0 ? 'disabled' : ''}>← Newer</button>
      <span class="meta">${offset + 1}–${offset + rows.length} of ${data.total}</span>
      <button id="next" ${offset + rows.length >= data.total ? 'disabled' : ''}>Older →</button>
    </div>` : `<div class="pager"><span class="meta">${rows.length} shown</span></div>`;

  el('list').innerHTML = items + pager;
  el('list').querySelectorAll('.row').forEach((node) => {
    node.onclick = () => select(Number(node.dataset.id));
  });
  const prev = el('prev'); const next = el('next');
  if (prev) prev.onclick = () => { offset = Math.max(0, offset - 50); load(); };
  if (next) next.onclick = () => { offset += 50; load(); };
}

function renderDetail(row) {
  const fields = [
    ['Type', row.type || row.category],
    ['Time', row.timestamp],
    ['Project', row.project_path],
    ['Session', row.session_id],
    ['Tags', row.tags],
  ].filter(([, v]) => v);
  el('detail').innerHTML = `
    <dl>${fields.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
    ${row.summary ? `<pre>${esc(row.summary)}</pre>` : ''}
    <pre>${esc(row.content || '(empty)')}</pre>`;
}

function select(id) {
  selected = id;
  el('list').querySelectorAll('.row').forEach((n) => {
    n.classList.toggle('sel', Number(n.dataset.id) === id);
  });
  const row = rows.find((r) => r.id === id);
  if (row && row.content !== undefined) { renderDetail(row); return; }
  // Only observations have a by-id endpoint; note ids live in another table.
  if (tab !== 'observations') { return; }
  api(`/api/observations/${id}`).then(renderDetail).catch(showError);
}

function showError(err) {
  el('list').innerHTML = `<div class="empty">Error: ${esc(err.message)}</div>`;
}

async function load() {
  el('list').innerHTML = '<div class="status">Loading…</div>';
  const params = {
    q: el('q').value.trim(),
    project: el('project').value,
    limit: 50,
    offset,
  };
  if (tab === 'observations') params.type = el('type').value;
  try {
    renderList(await api(`/api/${tab}`, params));
  } catch (err) { showError(err); }
}

async function boot() {
  if (!token) {
    // Opening the bare address is the likely mistake; say so instead of
    // letting the first API call fail with a bare 401.
    el('list').innerHTML = `<div class="empty">
      <strong>No access token in this URL.</strong><br><br>
      Memory can hold secrets, so the viewer only serves data to the link the
      CLI prints. Run <code>kimi-mcp-hub memory viewer</code> and open the URL
      it shows — it looks like <code>${esc(location.origin)}/?token=…</code>.
    </div>`;
    el('detail').innerHTML = '';
    return;
  }
  try {
    await refreshStats();
  } catch (err) { showError(err); return; }
  load();
}

// Counts and filter options come from the database, so they go stale as new
// observations land. Rebuilt on every reload, keeping the current selection.
async function refreshStats() {
  const s = await api('/api/stats');
  el('stats').textContent =
    `${s.observations.total_observations} observations · ` +
    `${s.observations.total_sessions} sessions · ` +
    `${s.memories.total_memories} notes`;

  const fill = (id, options) => {
    const select = el(id);
    const previous = select.value;
    select.length = 1;                     // keep the leading "All …" option
    for (const [value, label] of options) {
      select.insertAdjacentHTML('beforeend',
        `<option value="${esc(value)}">${esc(label)}</option>`);
    }
    select.value = previous;               // no-op if the option disappeared
  };

  fill('project', s.projects.map((p) => [p.project_path, `${shortPath(p.project_path)} (${p.count})`]));
  fill('type', s.types.map((t) => [t, t]));
}

let debounce;
el('q').oninput = () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => { offset = 0; load(); }, 250);
};
el('project').onchange = () => { offset = 0; load(); };
el('type').onchange = () => { offset = 0; load(); };
el('reload').onclick = () => refreshStats().then(load).catch(showError);
document.querySelectorAll('.tab').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    tab = btn.dataset.tab;
    el('type').disabled = tab !== 'observations';
    offset = 0;
    load();
  };
});
boot();
</script>
</body>
</html>
"""
