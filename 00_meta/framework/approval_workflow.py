from typing import Dict, Any

class ApprovalWorkflow:
    """Determines whether changes can be auto-enriched or require human sign-off."""

    @staticmethod
    def evaluate_approval(change_type: str, confidence: float) -> Dict[str, Any]:
        if change_type in ["REMOVED_DEVICE", "TOPOLOGY_CHANGE"] or confidence < 0.80:
            return {
                "auto_approved": False,
                "action": "PENDING_HUMAN_APPROVAL",
                "reason": f"High impact change type '{change_type}' or low confidence score ({confidence})."
            }
        return {
            "auto_approved": True,
            "action": "AUTO_ENRICH",
            "reason": f"Routine update '{change_type}' with high confidence ({confidence})."
        }
