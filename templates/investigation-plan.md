# Investigation Plan — Phase D.5

- **Live Verification Required:** {{ is_live_verification_required }}
- **KB Sufficient:** {{ is_kb_sufficient }}
- **Operational Cost Estimate:** {{ operational_cost_estimate }}

## 🔬 Active Hypotheses
{% for h in active_hypotheses %}
- **Hypothesis [{{ h.id }}]:** {{ h.hypothesis }} (Current Confidence: {{ h.confidence }})
  - *Verify Evidence:* {{ h.verification_evidence }}
  - *Falsify Evidence:* {{ h.falsification_evidence }}
{% endfor %}

## 🎯 Highest Information Gain Check
- **Target Device:** `{{ highest_information_gain_check.target_device }}`
- **Check ID:** `{{ highest_information_gain_check.check_id }}`
- **Rationale:** {{ highest_information_gain_check.rationale }}

## 📋 Minimum Devices & Command Sequence
- **Target Devices:** {{ minimum_devices_required | join(", ") }}
- **Command Sequence:**
{% for cmd in command_sequence %}
  1. `{{ cmd }}`
{% endfor %}

## 🛑 Stop Conditions & Expected Confidence
- **Expected Confidence Gain:** {{ expected_confidence_gain }}
- **Stop Conditions:**
{% for stop in stop_conditions %}
  - {{ stop }}
{% endfor %}
