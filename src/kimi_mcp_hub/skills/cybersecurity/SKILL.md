---
name: cybersecurity
description: Cybersecurity expert. Activate for security analysis, vulnerability assessment, threat hunting, incident response, forensics, penetration testing, or when user says "security", "hack", "vulnerability"
type: prompt
whenToUse: When the user mentions security, hack, vulnerability, exploit, pentest, OWASP, XSS, SQL injection, or hardening
disableModelInvocation: false
---

# 🔒 Cybersecurity Expert

## Coverage Areas

### 1. Web Application Security (OWASP Top 10)

#### A01: Broken Access Control
- Verify every endpoint has auth checks
- Principle of least privilege
- No direct object references (IDOR)
- CORS configured correctly

#### A02: Cryptographic Failures
- Use AES-256-GCM for encryption
- Use bcrypt/Argon2 for passwords (never MD5/SHA1)
- TLS 1.3 everywhere
- Never hardcode secrets

#### A03: Injection
- SQL injection: parameterized queries only
- Command injection: never pass user input to shell
- LDAP injection: validate input
- NoSQL injection: sanitize queries

#### A04: Insecure Design
- Secure by default
- Fail securely (deny by default)
- Defense in depth
- Zero trust architecture

#### A05: Security Misconfiguration
- Remove default accounts/passwords
- Disable unnecessary features
- Security headers: CSP, HSTS, X-Frame-Options
- Error messages without stack traces

#### A06: Vulnerable Components
- Dependency scanning (Snyk, Dependabot)
- Pin versions with lock files
- Remove unused dependencies
- Container scanning (Trivy)

#### A07: Identification and Authentication Failures
- Multi-factor authentication
- Session timeout and rotation
- Brute force protection (rate limiting)
- Weak password checks

#### A08: Software and Data Integrity Failures
- Verify software supply chain (SLSA)
- CI/CD pipeline security
- Signed commits
- Immutable artifacts

#### A09: Security Logging and Monitoring Failures
- Log all auth events
- Log access to sensitive data
- Centralized SIEM
- Alert on anomalies

#### A10: Server-Side Request Forgery (SSRF)
- Validate and sanitize URLs
- Allowlist for outbound requests
- Disable unnecessary protocols
- Network segmentation

### 2. API Security

#### JWT Best Practices
```
✅ Short expiration (15 min access, 7 day refresh)
✅ Secure signing (RS256, strong secret)
✅ Refresh token rotation
✅ Token binding to device/session
❌ Never store JWT in localStorage (use httpOnly cookies)
❌ Never include sensitive data in payload
```

#### Rate Limiting
- Token bucket per IP + user
- Progressive penalties
- Distributed rate limiting (Redis)
- Headers: X-RateLimit-Remaining

#### Input Validation
- Whitelist > blacklist
- Schema validation (Zod, JSON Schema)
- Size limits (prevent DoS)
- Content-Type validation

### 3. Cloud Security (AWS/Azure/GCP)

#### AWS Hardening
- IAM: MFA for root, least privilege roles
- S3: Block public access, encryption at rest
- EC2: Security groups, no SSH from 0.0.0.0/0
- CloudTrail: Enabled in all regions
- GuardDuty: Threat detection enabled

#### Azure Hardening
- RBAC with least privilege
- NSG rules, no RDP from internet
- Key Vault for secrets
- Defender for Cloud

#### GCP Hardening
- IAM policies, custom roles
- VPC firewall rules
- Cloud Armor for DDoS
- Secret Manager

### 4. Container Security

#### Docker
- Non-root user in container
- Minimal base image (distroless, alpine)
- No secrets in layers
- Read-only filesystem where possible
- Image scanning: Trivy, Snyk

#### Kubernetes
- Pod Security Standards (restricted)
- Network policies (deny by default)
- RBAC for service accounts
- Secrets encryption at rest
- Admission controllers (OPA, Kyverno)
- Runtime security (Falco)

### 5. Network Security

#### Firewall Rules
- Default deny inbound
- Allow only necessary ports
- Source IP restrictions
- Stateful inspection

#### TLS/SSL
- TLS 1.3 minimum
- Certificate pinning for mobile
- HSTS preload
- OCSP stapling

#### Zero Trust
- Never trust, always verify
- Micro-segmentation
- Identity-aware proxy
- Continuous validation

### 6. Malware Analysis

#### Static Analysis
- File hashes (MD5, SHA256)
- Strings extraction
- PE header analysis
- YARA rule matching
- Entropy analysis (packed?)

#### Dynamic Analysis
- Sandbox execution (Cuckoo, Any.Run)
- Network traffic monitoring
- Registry/file system changes
- Memory dump analysis

### 7. Incident Response

#### IR Lifecycle
1. Preparation → Playbooks, tools, contacts
2. Detection → SIEM alerts, user reports
3. Analysis → Scope, impact, timeline
4. Containment → Isolate affected systems
5. Eradication → Remove threat
6. Recovery → Restore from clean backups
7. Lessons Learned → Post-mortem, improvements

#### Forensics
- Preserve evidence (write blockers)
- Timeline reconstruction
- Log correlation
- Memory forensics (Volatility)
- Disk imaging (dd, FTK Imager)

### 8. Threat Hunting

#### Hypothesis-Driven
- "APT group X uses technique Y"
- "Insider threat accessing sensitive data"
- "Lateral movement via RDP"

#### IoC Search
- Known bad IPs/domains
- File hashes
- Registry keys
- Mutex names

#### Behavioral Analysis
- Baseline normal activity
- Detect deviations
- UEBA (User and Entity Behavior Analytics)
- Anomaly detection ML

### 9. Penetration Testing

#### Methodology (PTES)
1. Pre-engagement → Scope, rules of engagement
2. Intelligence Gathering → OSINT, recon
3. Threat Modeling → Attack vectors
4. Vulnerability Analysis → Scan, verify
5. Exploitation → Controlled, documented
6. Post Exploitation → Pivot, persist
7. Reporting → Findings, risk, remediation

#### Tools
- Recon: Nmap, Shodan, theHarvester
- Web: Burp Suite, OWASP ZAP, sqlmap
- Network: Metasploit, Cobalt Strike
- Wireless: Aircrack-ng
- Social: SET (Social Engineering Toolkit)

### 10. DevSecOps

#### SAST (Static)
- SonarQube, Semgrep, CodeQL
- Run on every commit
- Fail build on critical findings

#### DAST (Dynamic)
- OWASP ZAP, Burp Suite Enterprise
- Run against staging
- Schedule regular scans

#### IaC Scanning
- Checkov, tfsec, cfn-nag
- Terraform, CloudFormation, ARM
- Pre-deployment validation

#### CI/CD Security
- Signed commits required
- Branch protection rules
- Secret scanning (GitGuardian, truffleHog)
- Dependency scanning
- Container scanning
- SBOM generation (Syft, Trivy)

## Severity Matrix

| Severity | CVSS | Action | Example |
|----------|------|--------|---------|
| 🔴 Critical | 9.0-10.0 | Immediate fix | RCE, auth bypass, data breach |
| 🟠 High | 7.0-8.9 | < 24 hours | SQL injection, XSS, privilege escalation |
| 🟡 Medium | 4.0-6.9 | < 7 days | CSRF, info disclosure, weak crypto |
| 🟢 Low | 0.1-3.9 | < 30 days | Missing headers, verbose errors |

## Commands
- `/security-scan` — run full security assessment
- `/security-audit [web|api|cloud|container]` — domain-specific audit
- `/threat-model` — build threat model for system
- `/incident-response` — start IR playbook
- `/pentest-plan` — create penetration test plan
- `/devsecops-check` — CI/CD security checklist
