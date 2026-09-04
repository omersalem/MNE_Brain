# FMC 7.7.0 — REST API Automation

Covers: how to access the API (browser, curl, Postman, Python), authentication, common
endpoint patterns, and a full worked automation example. This is the real "CLI-equivalent"
for policy/object automation on FMC — use this instead of inventing CLI syntax for config
tasks.

**For the complete list of every API resource and what job it performs** (objects, policies,
devices, HA/clustering, deployment, health, chassis, troubleshooting, TID, licensing,
search, etc.) — see `references/rest-api-endpoint-catalog.md`. This file covers *how to
connect and call the API*; that file covers *everything you can call once connected*.

## Table of Contents
1. Three ways to access the API
2. Enabling & accessing the API
3. Authentication (token-based)
4. Domain UUID
5. Common endpoint patterns
6. Example: full auth → create object → deploy flow (Python)
7. Rate limits & best practices
8. API Explorer

---

## 1. Three ways to access the API

**a) Browser — API Explorer (no coding, good for one-off calls or learning a schema):**
```
https://<fmc-ip>/api/api-explorer
```
Log in with an FMC account (same credentials as GUI, but see the session-conflict warning
below), browse to a resource, fill in fields, and execute directly from the browser. Best
first stop when Omar wants to see the exact JSON a resource expects before scripting it.

**b) curl / any HTTP client (quick checks, shell scripting):**
```bash
# Get a token
curl -k -X POST -u 'apiuser:apipass' \
  https://<fmc-ip>/api/fmc_platform/v1/auth/generatetoken -D headers.txt -o /dev/null -s
grep -i x-auth-access-token headers.txt

# Use it
curl -k -H "X-auth-access-token: <token>" \
  https://<fmc-ip>/api/fmc_config/v1/domain/<DOMAIN_UUID>/object/networks
```

**c) A scripting language (Python/PowerShell/etc.) — the right choice for anything repeated,
scheduled, or involving more than a couple of calls.** See the full worked example in
section 6. This is what Omar would use for something like "script the creation of monthly
firewall audit object usage reports" or "auto-tag new branch network objects."

Postman (or any REST client) also works fine and can import the OpenAPI/Swagger spec pulled
from the API Explorer if Omar wants a GUI-based request builder instead of curl.

---

## 2. Enabling & accessing the API

The REST API is **enabled by default** on FMC 7.7.0. Base API Explorer URL (browsable, also
lets you generate sample code via CodeGen/OpenAPI spec):

```
https://<fmc-ip-or-hostname>/api/api-explorer
```

Base API path for programmatic calls:

```
https://<fmc-ip-or-hostname>/api/fmc_config/v1/domain/<DOMAIN_UUID>/...
https://<fmc-ip-or-hostname>/api/fmc_platform/v1/...          # platform-level (auth, audit, etc.)
```

**Important:** an FMC account **cannot use the API and the web GUI session simultaneously**
— logging into one silently logs the other out. Use a **separate dedicated API account**
(not `admin`, and not whatever account Omar uses for daily GUI work) with only the
permissions the automation actually needs.

---

## 3. Authentication (token-based)

```bash
# Step 1: obtain an auth token + refresh token (basic auth on this one call only)
curl -k -X POST \
  -u '<api-username>:<api-password>' \
  https://<fmc-ip>/api/fmc_platform/v1/auth/generatetoken \
  -D headers.txt

# Response headers include:
#   X-auth-access-token: <token>
#   X-auth-refresh-token: <refresh-token>
#   DOMAIN_UUID: <uuid>

# Step 2: use the access token on all subsequent calls
curl -k -X GET \
  -H "X-auth-access-token: <token>" \
  https://<fmc-ip>/api/fmc_config/v1/domain/<DOMAIN_UUID>/object/networks
```

- Tokens are valid **30 minutes** and can be **refreshed up to 3 times** before you must
  re-authenticate with username/password again.
- To refresh: POST to `/api/fmc_platform/v1/auth/refreshtoken` with both
  `X-auth-access-token` and `X-auth-refresh-token` headers set.

---

## 4. Domain UUID

Almost every config-object endpoint is scoped under a domain:

```
/api/fmc_config/v1/domain/<DOMAIN_UUID>/...
```

Get `DOMAIN_UUID` from the auth response headers after login (or from
`/api/fmc_platform/v1/info/domain` if you need to enumerate domains in a multidomain
deployment). In a single-domain (Global) deployment there's just the one UUID to grab once
and reuse.

---

## 5. Common endpoint patterns

```
# Objects
GET/POST    /object/networks
GET/POST    /object/hosts
GET/POST    /object/ports
GET/POST    /object/networkgroups

# Access Control Policy
GET/POST    /policy/accesspolicies
GET/POST    /policy/accesspolicies/<policyId>/accessrules

# NAT
GET/POST    /policy/ftdnatpolicies
GET/POST    /policy/ftdnatpolicies/<policyId>/autonatrules
GET/POST    /policy/ftdnatpolicies/<policyId>/manualnatrules

# Devices
GET         /devices/devicerecords
GET/PUT     /devices/devicerecords/<deviceId>

# Deploy
GET         /deployment/deployabledevices        # what's out of date
POST        /deployment/deploymentrequests        # kick off a deploy

# Health / status (useful for monitoring scripts)
GET         /health/alerts
GET         /health/metrics
```

`GET ALL` (a GET with no object ID) returns every object of that type — treat it as
expensive/paginated on large object sets; use filters where the endpoint supports them.

This is just a starter set. **For every resource FMC 7.7.0 exposes — objects, policies,
devices, HA/clustering, templates, deployment, health, chassis, troubleshooting/packet
tracer, threat intelligence, licensing, search, and more — see the full
`references/rest-api-endpoint-catalog.md`**, organized by category with the job each
endpoint performs.

---

## 6. Example: full auth → create object → deploy flow (Python)

```python
import requests
requests.packages.urllib3.disable_warnings()

FMC = "https://10.10.10.5"
USER, PASS = "api_svc_account", "REDACTED"

# 1. Authenticate
r = requests.post(f"{FMC}/api/fmc_platform/v1/auth/generatetoken",
                   auth=(USER, PASS), verify=False)
token = r.headers["X-auth-access-token"]
domain_uuid = r.headers["DOMAIN_UUID"]
headers = {"X-auth-access-token": token, "Content-Type": "application/json"}

# 2. Create a network object
payload = {
    "name": "MNE-Branch-LAN",
    "value": "10.20.30.0/24",
    "type": "Network"
}
r = requests.post(
    f"{FMC}/api/fmc_config/v1/domain/{domain_uuid}/object/networks",
    headers=headers, json=payload, verify=False
)
r.raise_for_status()
print("Created object:", r.json()["id"])

# 3. Check which devices are out of date
r = requests.get(
    f"{FMC}/api/fmc_config/v1/domain/{domain_uuid}/deployment/deployabledevices",
    headers=headers, verify=False
)
deployable = r.json().get("items", [])

# 4. Trigger a deploy against those devices
if deployable:
    device_ids = [d["device"]["id"] for d in deployable]
    deploy_payload = {"type": "DeploymentRequest",
                       "deviceList": device_ids,
                       "forceDeploy": False, "ignoreWarning": True}
    r = requests.post(
        f"{FMC}/api/fmc_config/v1/domain/{domain_uuid}/deployment/deploymentrequests",
        headers=headers, json=deploy_payload, verify=False
    )
    print("Deploy queued:", r.status_code, r.json())
```

Swap `verify=False` for a real CA-validated cert in anything beyond a lab/PoC — for a
government network deployment, treat cert validation as non-negotiable.

---

## 7. Rate limits & best practices (from Cisco's own guidance)

- **Rate limits (fixed):** up to 300 GET requests/minute per source IP; only **one**
  non-GET (PUT/POST/DELETE) request at a time per device; max 10 concurrent connections per
  IP. Exceeding any of these returns HTTP 429 ("Too Many Requests" or "Too Many Writes").
- **Payload limit:** 2,048,000 bytes per request (both raw API and API Explorer) — larger
  payloads return HTTP 422.
- Keep UI users and API users **separate**; don't reuse the `admin` account for API access.
  An account **cannot use the GUI and the API/API Explorer at the same time** — logging into
  one silently logs the other out.
- Give API users **only the permissions they need** for the task (least privilege) — API
  permissions map 1:1 to the same RBAC roles used for GUI accounts.
- Always **validate/sanitize JSON** returned from the server before acting on it — it can
  contain embedded executable content in some fields.
- If running FMC in **CC/UCAPL mode**, disable REST API access on FMC and managed devices
  entirely — it's incompatible with that compliance posture.
- Batch/paginate large `GET ALL` calls (use `offset`/`limit`, default page size is 25,
  max 1000) rather than hammering the API in a tight loop — especially relevant on a
  production ministry FMC that's also serving GUI users concurrently.
- 401 errors mean an invalid/expired session — re-authenticate rather than retrying blindly;
  429 means you're writing too fast — back off and retry with delay.

---

## 8. API Explorer

Browsable, interactive documentation of every endpoint FMC 7.7.0 supports, generated from the
OpenAPI spec — the fastest way to confirm exact field names/required parameters for an
endpoint before scripting against it:

```
https://<fmc-ip>/api/api-explorer
```

You can also pull the raw OpenAPI JSON spec from the Explorer and run it through Swagger's
CodeGen utility to generate client stubs in Python, Java, Perl, etc. Cisco DevNet also hosts
supplementary docs/examples: https://developer.cisco.com/secure-firewall/management-center/
