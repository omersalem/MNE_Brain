# BIG-IP 17.5.x — Modern Configuration Utility (TMUI) Full Navigation Map

## Top-Level Menu Structure

```
Main Menu (left sidebar)
├── Dashboard
├── iApps
│   ├── Application Services
│   └── Templates
├── Local Traffic (LTM)
│   ├── Virtual Servers
│   │   ├── Virtual Server List
│   │   └── Policies
│   ├── Pools
│   ├── Nodes
│   ├── Profiles
│   │   ├── Services (HTTP, HTTPS, TCP, UDP, FastHTTP, FastL4)
│   │   ├── SSL (Client, Server)
│   │   ├── Content (OneConnect, Stream, HTML, XML)
│   │   ├── Protocol (HTTP Compression, Web Acceleration)
│   │   └── Other (Analytics, Classification, DNS)
│   ├── iRules
│   ├── Policies
│   └── Traffic Class
│
├── Security
│   ├── Overview (Security Dashboard)
│   ├── Guided Configuration             ← QUICK SETUP
│   │   └── Web Application Protection
│   │
│   ├── Application Security (ASM / Advanced WAF)
│   │   ├── Security Policies
│   │   │   └── Policies List            ← MAIN POLICY LIST
│   │   ├── Policy Building
│   │   │   ├── Traffic Learning         ← SUGGESTIONS / POLICY BUILDER
│   │   │   ├── Settings
│   │   │   └── Builder Options
│   │   ├── Blocking Settings            ← LAB: LEARN/ALARM/BLOCK
│   │   ├── Attack Signatures
│   │   │   ├── Attack Signature Sets
│   │   │   └── Attack Signatures List
│   │   ├── Sessions and Logins
│   │   │   ├── Login Pages List
│   │   │   ├── Brute Force Attack Prevention
│   │   │   └── Session Tracking
│   │   ├── URLs
│   │   │   └── Allowed HTTP URLs
│   │   ├── Parameters
│   │   │   └── Parameters List
│   │   ├── Cookies
│   │   │   └── Cookies List
│   │   ├── File Types
│   │   │   └── Allowed File Types
│   │   ├── Headers
│   │   ├── Methods
│   │   ├── Redirection Domains
│   │   ├── Content Profiles (JSON, XML, GraphQL)
│   │   ├── Data Guard (Sensitive Data Masking)
│   │   ├── Policy Properties
│   │   │   ├── General Settings
│   │   │   ├── IP Intelligence
│   │   │   ├── Geolocation Enforcement
│   │   │   ├── CSRF Protection
│   │   │   └── Response Codes
│   │   └── Response Pages (Custom Block Page)
│   │
│   ├── Bot Defense
│   │   ├── Bot Defense Profiles         ← CREATE BOT PROFILE
│   │   ├── Bot Signatures
│   │   └── Bot Defense Configuration
│   │
│   ├── DoS Protection
│   │   ├── Protection Profiles          ← CREATE DoS PROFILE
│   │   └── Quick Configuration
│   │
│   ├── Event Logs
│   │   ├── Application
│   │   │   ├── Requests                 ← VIEW BLOCKED/PASSED REQUESTS
│   │   │   ├── Bot Requests
│   │   │   └── DoS
│   │   └── Network
│   │       └── DoS
│   │
│   ├── Reporting
│   │   ├── Application
│   │   │   ├── Charts
│   │   │   ├── Requests
│   │   │   └── Brute Force Summary
│   │   └── DoS
│   │
│   ├── IP Intelligence
│   │   ├── Policies
│   │   └── Feed Lists
│   │
│   └── Network Firewall (AFM)
│       ├── Active Rules
│       ├── Policies
│       ├── Rules
│       └── Address Lists
│
├── Access (APM)
├── Network
│   ├── Interfaces
│   ├── VLANs
│   ├── Self IPs
│   ├── Routes
│   └── DNS
│
└── System
    ├── Platform
    ├── Configuration
    ├── Software Management              ← UPGRADE / INSTALL
    ├── Users
    ├── High Availability
    │   ├── Device Management
    │   └── Device Groups
    ├── SNMP
    ├── Logs
    └── Resource Provisioning            ← SET ASM TO NOMINAL
```

---

## Critical UI Differences: 17.x vs. Older Versions

| Feature | Old GUI (pre-14.x) | New GUI (17.x) |
|---|---|---|
| WAF policies | "Application Security" top menu | Security > Application Security |
| Event logs | "Application Security > Reporting" | Security > Event Logs > Application |
| Bot Defense | Not available in old | Security > Bot Defense |
| Guided Config | Not available | Security > Guided Configuration |
| DoS profiles | Under ASM | Security > DoS Protection (separate) |
| Policy apply | "Apply Policy" button same location | Top right yellow "Apply Policy" button |

---

## Virtual Server Security Tab

When editing a Virtual Server (Local Traffic > Virtual Servers > [VS Name]):

Tabs at the top:
- General Properties
- Configuration
- Resources
- **Security** ← This is where you attach WAF policy, DoS profile, Bot profile, Log profile

Under Security tab:
- **Application Security Policy**: Select policy from dropdown
- **Anti-Fraud Profile**: Link
- **Bot Defense Profile**: Select bot defense profile
- **DoS Protection Profile**: Select DoS profile
- **Log Profile**: Select logging profile (CRITICAL — must add log profile to see logs)
- **iRules**: Attach iRules

---

## Apply Policy — Where and When

The **Apply Policy** button appears:
- Top right of any ASM policy editing screen (yellow/orange button)
- Also accessible: Security > Application Security > Security Policies > [Policy] > Apply Policy

**You MUST click Apply Policy after:**
- Adding/removing URLs, parameters, file types, cookies
- Changing blocking settings
- Adding/removing signature sets
- Changing enforcement mode
- Any policy change

Without applying, changes are pending but NOT active.

---

## Response Pages (Custom Block Page)

**Path:** Security > Application Security > [Policy Name] > Response Pages

- **Default**: F5 default block page
- **Custom**: Upload HTML
- **Redirect**: Redirect to a URL instead of showing block page
- **SOAP Fault**: For SOAP/XML applications
- **REST**: For REST API applications (returns JSON error)

The block response includes the **Support ID** by default — this is how users report blocked requests.

---

## Logging Profile Configuration

**Path:** Security > Event Logs > Logging Profiles > Create

Important: Without a logging profile attached to the virtual server, you will NOT see any WAF events in the GUI.

Required settings for full visibility:
- **Application Security**: Enabled
  - Request Type: All Requests (for testing) or Illegal Requests (for production)
  - Response Logging: Enabled (optional, high overhead)
- **DoS Protection**: Enabled
- **Bot Defense**: Enabled
- **Storage Destination**: Local (for GUI) or Remote Syslog
