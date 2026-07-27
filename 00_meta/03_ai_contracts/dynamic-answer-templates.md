# Dynamic Answer Templates & Contracts

> Every AI answer MUST adhere strictly to the response template designated for its query route. Only sections that add direct diagnostic or explanatory value are exposed.

## Route: Explanation
```markdown
**Answer:** <Direct, concise concept summary in 1-2 sentences>
**Related Components:** <Primary linked architecture components>
**References:** <Canonical knowledge note links>
```

## Route: Topology
```markdown
**Path:** <End-to-end traversal sequence>
**Dependencies:** <Direct component dependencies>
**Evidence:** <Documented or live structural source>
```

## Route: Asset Lookup
```markdown
**Asset Details:** <Key metadata and IP/FQDN mapping>
**Status:** <Documented status and freshness>
**References:** <Canonical note reference>
```

## Route: Incident
```markdown
**Status:** Healthy | Degraded | Failed | Unknown
**Evidence:** <Concise, attributable facts with trust tier>
**Confidence:** High | Medium | Low
**Unknowns:** <Unresolved facts affecting conclusion>
**Next Check:** <Highest information gain check>
**Action:** <Required remediation or escalation step>
```

## Route: Troubleshooting
```markdown
**Status:** Healthy | Degraded | Failed | Unknown
**Diagnosis:** <Root cause or active hypothesis>
**Evidence:** <Supporting evidence list with trust tier>
**Confidence:** High | Medium | Low
**Unknowns:** <Unverified items>
**Recommended Next Check:** <Single minimal check>
```

## Route: Health Check
```markdown
**Status:** Healthy | Degraded | Failed
**Telemetry:** <Summary of key metrics or check results>
**Findings:** <Active anomalies or clean confirmation>
**Next Check:** <Routine or follow-up check>
```

## Route: Review
```markdown
**Item:** <Target document or artifact>
**Metadata:** <Owner, trust tier, last verified date>
**Findings:** <Audit results, gaps, or compliance status>
**Freshness:** <Current vs stale threshold>
```

## Route: Remediation
```markdown
**Proposal:** <Intended change description>
**Target:** <Affected entity ID>
**Risk Level:** Low | Medium | High
**Approval State:** Pending Approval
**Rollback Plan:** <Step-by-step rollback procedure>
**Validation Plan:** <Post-change verification check>
```
