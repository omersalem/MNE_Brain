import diff_engine
import conflict_resolver
import relationship_sync
import quality_evaluator
import version_history
import approval_workflow
import sync_reporter

class SyncEngine:
    """Main orchestrator for Continuous Knowledge Synchronization."""

    def __init__(self, vault_root: str):
        self.vault_root = vault_root
        self.history = version_history.VersionHistory(vault_root)
        self.reporter = sync_reporter.SyncReporter(vault_root)

    def run_synchronization(self, vault_canonical_notes: list, new_telemetry_batch: list) -> dict:
        all_changes = []
        
        for new_item in new_telemetry_batch:
            # Find matching vault item
            match = next((item for item in vault_canonical_notes if item.get("id") == new_item.get("id")), {})
            diffs = diff_engine.DiffEngine.compare_states(match, new_item)
            
            for d in diffs:
                appr = approval_workflow.ApprovalWorkflow.evaluate_approval(d["type"], d["confidence"])
                d["approval_status"] = appr["action"]
                all_changes.append(d)
                
                # Record to Version History
                self.history.record_change(
                    entity_id=new_item.get("id", "UNKNOWN"),
                    field=d["field"],
                    old_val=d["old_value"],
                    new_val=d["new_value"],
                    source="Live_Read_Sync",
                    confidence=d["confidence"]
                )

        # Quality Evaluation
        quality_metrics = quality_evaluator.QualityEvaluator.evaluate_vault_quality(vault_canonical_notes)
        
        # Report Generation
        report_file = self.reporter.generate_sync_report(quality_metrics, all_changes)

        return {
            "status": "success",
            "quality_metrics": quality_metrics,
            "changes_processed": len(all_changes),
            "sync_report": report_file
        }
