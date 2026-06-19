---
name: security-guidance
description: 3-layer security scanning guidance for file edits, model turns, and commits.
type: prompt
whenToUse: When the user edits files and asks for security validation or automatic security scanning.
disableModelInvocation: false
---
# 🔒 Security Guidance — 3-Layer Scan

## Layer 1: File Edit Scan (real-time)

When ANY file is edited, check for:

### Dangerous Functions
- `eval()`, `exec()`, `Function()` constructor
- `os.system()`, `subprocess.call(shell=True)`, `child_process.exec()`
- `dangerouslySetInnerHTML`, `innerHTML = ` without sanitization
- `pickle.loads()`, `yaml.load(unsafe)`, `unserialize()`
- `setTimeout(string)`, `setInterval(string)`
- `new Function()`, `vm.runInContext()`

### Unsafe Patterns
- SQL string concatenation: `"SELECT * FROM users WHERE id = " + userId`
- Command injection: `exec("ping " + hostname)`
- Path traversal: `fs.readFile(req.query.path)`
- SSRF: `fetch(req.query.url)` without allowlist
- Weak crypto: `md5()`, `sha1()` for passwords, `Math.random()` for tokens
- Hardcoded secrets: `password = "123456"`, `api_key = "sk-..."`
- CORS wildcard: `Access-Control-Allow-Origin: *` with credentials
- Missing CSRF tokens on state-changing endpoints

### Auto-fix suggestions
- `eval()` → `JSON.parse()` or structured parsing
- `os.system()` → `subprocess.run()` with array args
- `dangerouslySetInnerHTML` → `textContent` or DOMPurify
- SQL concat → parameterized queries
- `Math.random()` → `crypto.randomBytes()`

## Layer 2: Post-Model Turn Scan (diff review)

After AI generates code, scan the git diff for:

### Auth & Access Control
- Missing authentication checks on new endpoints
- Missing authorization (role checks)
- Privilege escalation paths
- Mass assignment vulnerabilities

### Injection Vectors
- New SQL injection points
- New XSS vectors (reflected, stored, DOM)
- Command injection in new code
- LDAP, XPath, NoSQL injection

### Data Protection
- PII logged or exposed in responses
- Secrets in error messages
- Unencrypted sensitive data in transit or rest
- Missing input validation

### Crypto
- New weak hash usage
- Custom crypto instead of standard libs
- Missing TLS/SSL verification
- Predictable tokens/IDs

## Layer 3: Commit/Push Scan (contextual)

Before commit, scan surrounding context:

### Related Files
- Are sanitizers applied consistently?
- Do validators exist and are they used?
- Are tests covering security paths?
- Is logging sufficient for audit?

### Configuration
- New env vars — are they documented?
- New dependencies — are they audited?
- New ports/services — are they firewalled?
- New CORS origins — are they intentional?

### Deployment
- Secrets in Docker layers?
- Hardcoded IPs/URLs?
- Debug mode enabled in prod?
- Default passwords unchanged?

## Severity Levels

| Level | Color | Action |
|-------|-------|--------|
| 🔴 Critical | Block commit | Remote code execution, auth bypass, data breach |
| 🟠 High | Require review | SQL injection, XSS, privilege escalation |
| 🟡 Medium | Warning | Missing validation, weak crypto, info disclosure |
| 🟢 Low | Note | Missing headers, logging gaps, style issues |

## Commands
- `/security-scan` — manual full scan
- `/security-level [critical|high|medium|low]` — set minimum threshold
- `/security-ignore [pattern]` — add exception (with justification)
- `/security-report` — generate security report for this session
