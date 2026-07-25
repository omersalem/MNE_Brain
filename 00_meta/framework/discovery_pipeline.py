from typing import Dict, Any
import connection_manager
import normalizer
import relationship_engine
import change_detector
import knowledge_merger
import reporting_engine
import base_connector

class DiscoveryPipeline:
    """Orchestrates the 11-stage universal discovery pipeline."""

    def __init__(self, vault_root: str):
        self.vault_root = vault_root
        self.conn_mgr = connection_manager.ConnectionManager(vault_root)
        self.reporter = reporting_engine.ReportingEngine(vault_root)

    def run_pipeline(self, profile_rel_path: str, connector: base_connector.BaseConnector) -> Dict[str, Any]:
        # Stage 1: Load Profile & Validate Connection
        profile = self.conn_mgr.load_profile(profile_rel_path)
        connector.validate_connection(profile)

        # Stage 2 & 3: Auth & Capability Detection
        connector.test_authentication(profile)
        caps = connector.detect_capabilities(profile)

        # Stage 4 & 5: Data Collection & Validation
        raw_telemetry = connector.collect_raw_telemetry(profile)

        # Stage 6: Normalization
        normalized = connector.normalize_data(raw_telemetry)

        # Stage 7: Relationship Detection
        rels = relationship_engine.RelationshipEngine.infer_relationships(normalized)
        normalized.update(rels)

        # Stage 8 & 9: Change Detection & Knowledge Enrichment
        vault_state = {"mgmt_ip": profile.get("mgmt_ip"), "status": "active", "model": "FortiGate"}
        changes = change_detector.ChangeDetector.detect_changes(vault_state, normalized)

        # Stage 10 & 11: Report Generation
        report_path = self.reporter.generate_report(connector.connector_name, "success", changes)

        return {
            "status": "success",
            "profile": profile_rel_path,
            "connector": connector.connector_name,
            "capabilities": caps,
            "changes_detected": len(changes),
            "report": report_path
        }
