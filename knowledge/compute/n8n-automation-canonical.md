---
id: "n8n-automation-server-01"
name: "n8n Workflow Automation Engine Server"
category: "compute"
aliases: ["n8n-automation", "n8n-server", "automation-server", "172.23.19.80"]
hostname: "n8n-automation-server-01"
fqdn: "n8n-automation-server-01.mne.gov.ps"
ip: "172.23.19.80"
vlan: "19"
services: ["n8n-workflows", "webhook-listener", "api-integrations", "alert-remediation"]
owner: "NOC Automation & Systems Engineering Team"
related_entities: ["vc-vmware-hq-01", "fw-fortigate-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — n8n Workflow Automation Engine Server

> **Entity ID:** `n8n-automation-server-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🤖 Workflow Automation Server Details
- **Hostname:** `n8n-automation-server-01`
- **Management IP:** `172.23.19.80`
- **Product:** n8n Enterprise Workflow Automation Engine
- **Port:** `5678/tcp`
- **Integrations:** Webhook Alert Listener, Zabbix Monitoring Triggers, Exchange Transport Alerts
