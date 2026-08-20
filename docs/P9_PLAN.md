# P9 Plan: Deep Diagnostics and Root-Cause Reasoning

P9 converts P8 authenticated access into bounded diagnostic evidence for eight Ministry domains.

1. Register exact read-only platform checks and normalizers.
2. Restrict one session to one scenario, one primary binding, at most three bindings, and four checks.
3. Normalize raw output into compact counts, states, and booleans, then discard the raw text.
4. Rank remaining checks by stage and information gain.
5. Build a sub-1,500-token AI handoff from accepted live evidence only.
6. Require AI conclusions to cite accepted evidence IDs.
7. Stop early only at evidence-bound confidence of at least 95%.
8. Expose planning and readiness through a non-connecting API and presentation-only GUI.
9. Live-validate every family and keep policy disabled afterward.

The families are branch WAN, SSL-VPN, web/F5 publishing, DNS/AD, Exchange, VMware, FMC/FTD security, and storage/backup/core switching. DC2, Exchange, vCenter REST, FMC REST, and Fujitsu SW1 now have exact bindings. Veeam is deliberately unattempted because this workstation has no path to it; the actual SAN controller and Fujitsu SW2 still require exact identity bindings.
