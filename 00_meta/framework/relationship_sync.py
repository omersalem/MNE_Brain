from typing import Dict, Any, List

class RelationshipSync:
    """Synchronizes Wiki graph edges [[Entity]] across infrastructure tiers."""

    @staticmethod
    def sync_relationships(entity_type: str, new_links: List[str], existing_links: List[str]) -> Dict[str, List[str]]:
        combined = list(set(existing_links + new_links))
        added = [link for link in new_links if link not in existing_links]
        removed = [link for link in existing_links if link not in new_links]

        return {
            "synchronized_links": combined,
            "links_added": added,
            "links_removed": removed
        }
