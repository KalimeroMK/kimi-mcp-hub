---
name: security-audit
description: >
  Security review and hardening. Activate when user says "security",
  "audit", "vulnerability", "secure this", "harden", "penetration test",
  or when reviewing code that handles auth, data, payments, or PII.
---

# 🔒 Security Audit

## Checklist

### Authentication
- [ ] Passwords hashed with bcrypt/Argon2 (not MD5/SHA1)
- [ ] JWT has expiration, signed with strong secret
- [ ] Refresh tokens rotated on use
- [ ] Rate limiting on login endpoints
- [ ] 2FA supported for sensitive accounts

### Authorization
- [ ] RBAC implemented (not just admin/user)
- [ ] Principle of least privilege
- [ ] Resource-level access checks (can User A see User B's data?)
- [ ] No mass assignment vulnerabilities

### Input Validation
- [ ] All user input validated (whitelist > blacklist)
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (output encoding, CSP headers)
- [ ] CSRF tokens on state-changing requests
- [ ] File upload restrictions (type, size, scan)

### Data Protection
- [ ] Encryption at rest (AES-256)
- [ ] Encryption in transit (TLS 1.3)
- [ ] PII masked in logs
- [ ] Secrets in env vars / vault (never in code)
- [ ] Backup encryption

### Dependencies
- [ ] `npm audit` / `pip-audit` / `safety check` clean
- [ ] No deprecated/unmaintained packages
- [ ] Pin versions (lock files)
- [ ] SCA tool scan (Snyk, Dependabot)

### Infrastructure
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] WAF configured
- [ ] Container scanning (Trivy)
- [ ] Network segmentation
- [ ] Logging and monitoring (SIEM)

## Severity Levels
- 🔴 Critical: Remote code execution, data breach
- 🟠 High: Auth bypass, privilege escalation
- 🟡 Medium: XSS, CSRF, information disclosure
- 🟢 Low: Missing headers, verbose errors
