# Advanced WAF Policy Templates — BIG-IP 17.5.x

## Available Templates

### 1. Rapid Deployment Policy (RDP)
**Use case:** Quick deployment with minimal initial false positives
- Enforcement mode: Transparent (switches to Blocking after learning)
- Signatures: Enabled in Alarm mode (staging)
- Learning: Automatic
- Good for: Non-critical applications, getting started fast
- Risk: Less strict, may miss some attacks initially

### 2. Fundamental Policy
**Use case:** Balanced protection for most web applications
- Enforcement: Blocking mode
- Signatures: Comprehensive set enabled
- HTTP protocol compliance: Enforced
- Attack types covered: OWASP Top 10 basics
- Good for: Standard web apps, internal applications

### 3. Comprehensive Policy
**Use case:** Maximum protection, strict enforcement
- Enforcement: Blocking mode
- All signature sets enabled
- HTTP protocol compliance: Strict
- Content type validation: Enabled
- JSON/XML parsing: Enabled
- Session tracking: Enabled
- Good for: Public-facing, high-risk applications

### 4. Blank Policy
**Use case:** Full manual customization
- No pre-configured settings
- Build everything from scratch
- Good for: Experienced WAF admins, specific compliance requirements

### 5. API Security Template (v17.x+)
**Use case:** REST API protection
- Focuses on JSON content
- Relaxes traditional HTML/form violations
- Enforces API-specific attack patterns
- Good for: Microservices, REST APIs, mobile app backends

### 6. OWASP Top 10 Template
**Use case:** Compliance-focused deployment
- Aligned with OWASP Top 10 (2021 edition as of v17.x)
- Includes the 3 new 2021 categories
- Good for: PCI-DSS compliance, audit requirements

---

## Policy Building Modes

### Manual Policy Building
- Admin manually reviews and accepts/rejects learning suggestions
- Full control over what is allowed
- Path: Security > Application Security > Policy Building > Traffic Learning

### Automatic Policy Building
- System automatically accepts high-confidence suggestions
- Faster time to protection
- Risk: May auto-allow malicious patterns if they appear legitimate
- Configure: Security > Application Security > Policy Building > Settings

### Policy Builder Speed Settings
- **Slow**: Conservative, higher confidence required
- **Medium**: Balanced (default)
- **Fast**: Aggressive, lower confidence threshold

---

## Entity Staging vs. Enforcement

**Staging** = Alarm but don't block (learn mode for individual entities)
**Enforcement** = Full block when violation detected

New entities added by Policy Builder start in **Staging** by default.
Entities move to **Enforcement** after sufficient traffic is seen.

To manually move an entity from staging to enforced:
- GUI: Security > Application Security > [entity type] > uncheck "Staging" checkbox
- TMSH: `tmsh modify asm policy <n> urls modify { /path { staging false } }`

---

## Signature Staging

New attack signatures downloaded in updates enter **Staging** for 7 days by default.
During staging, they alarm but don't block.
This prevents new signatures from causing sudden false positives.

```bash
# Check staging period setting
tmsh list asm policy <policy-name> | grep staging

# Disable staging for all signatures in policy (force immediate blocking)
tmsh modify asm policy <policy-name> signature-staging false

# Enable staging
tmsh modify asm policy <policy-name> signature-staging true
```

---

## OWASP Top 10 Coverage (2021) in BIG-IP 17.x

| OWASP Category | BIG-IP Coverage |
|---|---|
| A01: Broken Access Control | Session tracking, IP intelligence |
| A02: Cryptographic Failures | SSL enforcement, sensitive data masking (Data Guard) |
| A03: Injection (SQL, XSS, etc.) | Attack signatures |
| A04: Insecure Design | Policy builder, login page protection |
| A05: Security Misconfiguration | HTTP compliance, method enforcement |
| A06: Vulnerable Components | Threat Campaign signatures |
| A07: Authentication Failures | Brute force protection, credential stuffing |
| A08: Software Integrity Failures | File upload protection |
| A09: Logging Failures | Request logging, event correlation |
| A10: SSRF | SSRF Host configuration (added in 17.x) |

---

## Policy Diff and Comparison

```bash
# Compare two policies in GUI
# Security > Application Security > Policy Building > Compare Policies

# From TMSH
tmsh show asm policy <policy1> diff <policy2>
```

Requirements for policy diff:
- Same system or accessible via import
- Same language encoding
- Same protocol independence setting (HTTP vs HTTPS differentiation)
- Same case sensitivity setting
