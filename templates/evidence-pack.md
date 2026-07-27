# Evidence Pack

- **Question:** {{ question }}
- **Query Route:** {{ query_route }}
- **Generated At:** {{ generated_at }}

## 🎯 Resolved Entities
{% for entity in resolved_entities %}
- **ID:** `{{ entity.id }}` | **Type:** {{ entity.type }} | **Canonical Note:** `{{ entity.canonical_note }}`
{% else %}
- None (Concept Query)
{% endfor %}

## 📦 Collected Evidence Items
{% for item in evidence_items %}
### Item: `{{ item.id }}`
- **Source:** {{ item.source }}
- **Trust Tier:** {{ item.trust_tier }}
- **Observed At / Freshness:** {{ item.freshness }}
{% if item.summary %}
- **Summary:** {{ item.summary }}
{% endif %}

```markdown
{{ item.content_snippet }}
```
{% endfor %}

## ❓ Unknowns & Evidence Gaps
{% for unk in unknowns %}
- ⚠️ {{ unk }}
{% else %}
- None identified.
{% endfor %}
