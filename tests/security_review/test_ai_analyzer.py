"""
Unit and integration tests for SecurityAIAnalyzer (Batch 5).
Verifies Codex and Antigravity analysis, both-engine comparison, error isolation,
result schema validation, and incident chat opening.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory
from core.security_review.ai_analyzer import SecurityAIAnalyzer
from core.security_review.analysis_compare import SecurityAnalysisComparator
from core.security_review.analysis_pack import SecurityAnalysisPackBuilder
from core.security_review.contracts import (
    ReviewMode,
    RunState,
    SecurityReviewRequest,
    SecurityReviewRun,
    validate_contract,
)
from core.security_review.run_store import SecurityReviewRunStore

BASE = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def run_store(tmp_path):
    store_dir = tmp_path / "runs"
    return SecurityReviewRunStore(store_dir)


@pytest.fixture
def sample_incident(run_store):
    run_id = "sec-run-ai-test-01"
    run = SecurityReviewRun(
        run_id=run_id,
        request=SecurityReviewRequest(
            mode=ReviewMode.QUICK,
            collector_ids=["fortigate_core"],
        ).to_dict(),
        state=RunState.COMPLETED,
        stage="COMPLETED",
        created_at="2026-09-09T12:00:00+00:00",
        completed_at="2026-09-09T12:05:00+00:00",
        incident_counts={"total": 1, "critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0},
    )
    run_store.save_run(run)

    incidents = [
        Incident(
            incident_id="inc-brute-001",
            title="SSH Brute Force on Perimeter Gateway",
            severity=SeverityLevel.CRITICAL,
            source_device="FortiGate-Core-HQ",
            category=ThreatCategory.BRUTE_FORCE,
            first_seen="2026-09-09T12:00:00+00:00",
            last_seen="2026-09-09T12:04:00+00:00",
            description="Over 400 failed SSH authentication attempts from untrusted external IP.",
            action_taken="BLOCKED",
            event_count=412,
            attacker_ip="198.51.100.99",
            target="10.0.0.1",
            signature_family="SSH_BRUTE_FORCE",
            devices_involved=["FortiGate-Core-HQ"],
            branches_involved=["HQ-DataCenter"],
        ),
    ]
    recs = run_store.record_run_incidents(run_id, incidents)
    return recs[0].fingerprint, run_id


def test_single_engine_codex_analysis(run_store, sample_incident):
    fingerprint, run_id = sample_incident

    def fake_codex_invoker(prompt: str, pack: Dict[str, Any]) -> str:
        assert "<SECURITY_ANALYSIS_PACK>" in prompt
        assert pack["target_type"] == "INCIDENT"
        fp_str = pack["incident_fingerprints"][0]
        return f"""```json
{{
  "plain_summary": "High-frequency SSH dictionary attack observed targeting firewall management port.",
  "confidence": 0.92,
  "affected_systems": ["10.0.0.1", "FortiGate-Core-HQ"],
  "affected_users": ["root", "admin"],
  "affected_branches": ["HQ-DataCenter"],
  "affected_services": ["SSH"],
  "ranked_hypotheses": [
    {{
      "hypothesis": "Automated credential-stuffing botnet targeting external admin interface",
      "likelihood": "HIGH",
      "explanation": "High velocity failed auth events with sequential username patterns."
    }}
  ],
  "observations": {{
    "supporting": ["412 failed SSH attempts in 4 minutes", "Disposition BLOCKED by local rate-limiting"],
    "contradicting": []
  }},
  "missing_evidence": ["NetFlow records from upstream border router"],
  "recommended_diagnostics": ["diagnose sys session filter dport 22", "diagnose firewall iprope show 100004"],
  "immediate_actions": ["Block 198.51.100.99 permanently on upstream perimeter ACL", "Disable WAN SSH management"],
  "long_term_actions": ["Enforce SSH key-only auth or VPN requirement"],
  "relevant_steps": {{
    "cli": ["config system admin", "set trusthost1 10.0.0.0 255.255.0.0", "end"],
    "gui": ["System > Administrators > Edit Admin > Trusted Hosts"]
  }},
  "source_references": ["operations/security_review/incidents/{fp_str}.json"],
  "warnings": []
}}
```"""

    analyzer = SecurityAIAnalyzer(run_store=run_store, codex_invoker=fake_codex_invoker)
    response = analyzer.analyze_incident(fingerprint, engine="CODEX")

    assert response["engine"] == "CODEX"
    result = response["result"]
    assert result["status"] == "COMPLETED"
    assert result["confidence"] == 0.92
    assert len(result["ranked_hypotheses"]) == 1
    assert result["ranked_hypotheses"][0]["likelihood"] == "HIGH"
    assert len(result["recommended_diagnostics"]) == 2

    # Schema validation
    validate_contract(result, "security-analysis-result.schema.json")

    # Verify persistence
    saved = run_store.get_analysis(result["analysis_id"])
    assert saved is not None
    assert saved["analysis_id"] == result["analysis_id"]


def test_single_engine_antigravity_analysis(run_store, sample_incident):
    fingerprint, run_id = sample_incident

    def fake_antigravity_invoker(prompt: str, pack: Dict[str, Any]) -> str:
        assert "<SECURITY_ANALYSIS_PACK>" in prompt
        return """```json
{
  "plain_summary": "Antigravity analysis identifies external brute-force reconnaissance.",
  "confidence": 0.89,
  "affected_systems": ["10.0.0.1"],
  "ranked_hypotheses": [
    {
      "hypothesis": "Automated credential-stuffing botnet targeting external admin interface",
      "likelihood": "HIGH",
      "explanation": "Repeated failed logins matched brute-force heuristics."
    }
  ],
  "observations": {
    "supporting": ["Observed BLOCKED disposition across all events"],
    "contradicting": []
  },
  "missing_evidence": ["GeoIP intelligence for source IP"],
  "recommended_diagnostics": ["diagnose sys session filter dport 22"],
  "immediate_actions": ["Apply WAN access list restrict to VPN subnet"],
  "long_term_actions": ["Migrate management to OOB dedicated network"],
  "source_references": [],
  "warnings": []
}
```"""

    analyzer = SecurityAIAnalyzer(run_store=run_store, antigravity_invoker=fake_antigravity_invoker)
    response = analyzer.analyze_incident(fingerprint, engine="ANTIGRAVITY")

    assert response["engine"] == "ANTIGRAVITY"
    result = response["result"]
    assert result["status"] == "COMPLETED"
    assert result["confidence"] == 0.89
    validate_contract(result, "security-analysis-result.schema.json")


def test_both_engines_concurrent_execution_and_comparison(run_store, sample_incident):
    fingerprint, run_id = sample_incident
    packs_received = []

    def fake_codex(prompt: str, pack: Dict[str, Any]) -> str:
        packs_received.append(("codex", json.dumps(pack, sort_keys=True)))
        return """```json
{
  "plain_summary": "Codex assesses high-confidence automated brute-force attack.",
  "confidence": 0.90,
  "ranked_hypotheses": [
    {
      "hypothesis": "Automated credential brute-force from known scanning botnet",
      "likelihood": "HIGH",
      "explanation": "Repetitive failed logins"
    }
  ],
  "observations": {"supporting": ["Blocked status"], "contradicting": []},
  "missing_evidence": ["Upstream router BGP flows"],
  "recommended_diagnostics": ["diagnose sys session filter dport 22", "get system status"],
  "immediate_actions": ["Block source IP"],
  "long_term_actions": [],
  "source_references": [],
  "warnings": []
}
```"""

    def fake_antigravity(prompt: str, pack: Dict[str, Any]) -> str:
        packs_received.append(("antigravity", json.dumps(pack, sort_keys=True)))
        return """```json
{
  "plain_summary": "Antigravity assessment of SSH attack telemetry.",
  "confidence": 0.88,
  "ranked_hypotheses": [
    {
      "hypothesis": "Automated credential brute-force from known scanning botnet",
      "likelihood": "HIGH",
      "explanation": "Matches scanner behavior"
    },
    {
      "hypothesis": "Internal misconfigured administrative script",
      "likelihood": "LOW",
      "explanation": "External IP makes script error unlikely"
    }
  ],
  "observations": {"supporting": ["Blocked status"], "contradicting": []},
  "missing_evidence": ["Upstream router BGP flows", "Target auth log debug level"],
  "recommended_diagnostics": ["diagnose sys session filter dport 22", "show firewall policy"],
  "immediate_actions": ["Block source IP"],
  "long_term_actions": [],
  "source_references": [],
  "warnings": []
}
```"""

    analyzer = SecurityAIAnalyzer(
        run_store=run_store,
        codex_invoker=fake_codex,
        antigravity_invoker=fake_antigravity,
    )
    response = analyzer.analyze_incident(fingerprint, engine="BOTH")

    assert response["engine"] == "BOTH"
    assert "codex" in response
    assert "antigravity" in response
    assert "comparison" in response

    # Verify byte-equivalent analysis packs received by both adapters
    assert len(packs_received) == 2
    assert packs_received[0][1] == packs_received[1][1]

    # Verify comparison findings
    cmp = response["comparison"]
    assert cmp is not None
    assert len(cmp["common_conclusions"]) > 0
    assert any("brute-force" in c.lower() for c in cmp["common_conclusions"])
    assert len(cmp["antigravity_only_conclusions"]) == 1
    assert "Internal misconfigured administrative script" in cmp["antigravity_only_conclusions"][0]
    assert len(cmp["shared_diagnostics"]) >= 1
    assert any("dport 22" in d for d in cmp["shared_diagnostics"])
    assert len(cmp["unresolved_questions"]) >= 1

    # Verify comparison persisted
    saved_cmp = run_store.get_comparison(cmp["comparison_id"])
    assert saved_cmp is not None


def test_failed_engine_preserves_successful_result(run_store, sample_incident):
    fingerprint, run_id = sample_incident

    def failing_codex(prompt: str, pack: Dict[str, Any]) -> str:
        raise RuntimeError("Codex child process crashed unexpectedly.")

    def working_antigravity(prompt: str, pack: Dict[str, Any]) -> str:
        return """```json
{
  "plain_summary": "Antigravity analysis succeeded despite peer engine crash.",
  "confidence": 0.85,
  "ranked_hypotheses": [
    {"hypothesis": "Brute-force attack detected", "likelihood": "HIGH", "explanation": "Log volume"}
  ],
  "observations": {"supporting": [], "contradicting": []},
  "missing_evidence": [],
  "recommended_diagnostics": [],
  "immediate_actions": [],
  "long_term_actions": [],
  "source_references": [],
  "warnings": []
}
```"""

    analyzer = SecurityAIAnalyzer(
        run_store=run_store,
        codex_invoker=failing_codex,
        antigravity_invoker=working_antigravity,
    )
    response = analyzer.analyze_incident(fingerprint, engine="BOTH")

    assert response["codex"]["status"] == "FAILED"
    assert "crashed unexpectedly" in response["codex"]["plain_summary"]

    assert response["antigravity"]["status"] == "COMPLETED"
    assert response["antigravity"]["confidence"] == 0.85
    validate_contract(response["antigravity"], "security-analysis-result.schema.json")

    # Antigravity result is preserved and retrievable
    saved = run_store.get_analysis(response["antigravity"]["analysis_id"])
    assert saved is not None


def test_partial_unstructured_text_response(run_store, sample_incident):
    fingerprint, run_id = sample_incident

    def unstructured_invoker(prompt: str, pack: Dict[str, Any]) -> str:
        return (
            "I investigated the incident. The target 10.0.0.1 is being probed by 198.51.100.99. "
            "It appears to be a brute force attack, but rate limiting held up."
        )

    analyzer = SecurityAIAnalyzer(run_store=run_store, codex_invoker=unstructured_invoker)
    response = analyzer.analyze_incident(fingerprint, engine="CODEX")

    result = response["result"]
    assert result["status"] == "PARTIAL"
    assert "brute force attack" in result["plain_summary"]
    assert len(result["warnings"]) > 0
    assert result["confidence"] == 0.5
    validate_contract(result, "security-analysis-result.schema.json")


def test_open_incident_chat(run_store, sample_incident):
    fingerprint, run_id = sample_incident
    analyzer = SecurityAIAnalyzer(run_store=run_store)
    chat_info = analyzer.open_incident_chat(fingerprint, engine="codex")

    assert "thread_id" in chat_info
    assert "title" in chat_info
    assert chat_info["fingerprint"] == fingerprint
    assert chat_info["engine"] == "codex"
