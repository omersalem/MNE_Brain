from typing import Dict, Any

class QualityEvaluator:
    """Evaluates knowledge completeness, consistency, freshness, and confidence."""

    @staticmethod
    def evaluate_vault_quality(canonical_notes: list) -> Dict[str, Any]:
        total_notes = len(canonical_notes)
        if total_notes == 0:
            return {"vault_health_score": 1.0, "total_notes": 0}

        verified_count = 0
        total_confidence = 0.0
        missing_info_count = 0

        for note in canonical_notes:
            conf = note.get("confidence_score", 0.8)
            total_confidence += conf
            if conf >= 0.9:
                verified_count += 1
            if note.get("confidence_score", 1.0) < 0.7:
                missing_info_count += 1

        avg_confidence = round(total_confidence / total_notes, 2)
        freshness_ratio = round(verified_count / total_notes, 2)
        health_score = round((avg_confidence * 0.6) + (freshness_ratio * 0.4), 2)

        return {
            "total_notes": total_notes,
            "verified_notes": verified_count,
            "average_confidence": avg_confidence,
            "freshness_ratio": freshness_ratio,
            "missing_info_gaps": missing_info_count,
            "vault_health_score": health_score
        }
