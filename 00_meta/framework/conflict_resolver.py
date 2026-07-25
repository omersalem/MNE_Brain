from typing import Dict, Any, List

class ConflictResolver:
    """Resolves conflicts across multiple knowledge sources using weighted confidence."""

    SOURCE_WEIGHTS = {
        "LIVE_READ_TELEMETRY": 0.95,
        "EXPORTED_DEVICE_CONFIG": 0.85,
        "OFFICIAL_MANUAL_DOC": 0.75,
        "HISTORICAL_NOTE": 0.60
    }

    @classmethod
    def resolve_conflict(cls, field: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        highest_score = 0.0
        best_source = None
        
        for src in sources:
            score = src.get("confidence", 0.5) * cls.SOURCE_WEIGHTS.get(src.get("source_type"), 0.5)
            if score > highest_score:
                highest_score = score
                best_source = src

        requires_approval = highest_score < 0.80 or len(sources) > 2
        
        return {
            "field": field,
            "resolved_value": best_source.get("value") if best_source else None,
            "winning_source": best_source.get("source_name") if best_source else "Unknown",
            "confidence_score": round(highest_score, 2),
            "requires_human_approval": requires_approval
        }
