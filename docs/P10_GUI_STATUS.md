# P10 GUI Status

The P10 GUI is presentation-only. It lists redacted operation metadata and renders the complete server-prepared immutable package: exact target and identity evidence, intended change, scope and affected systems, dependencies/prohibited conditions, risk and expected impact, prechecks, backup/snapshot claim, exact ordered transactions, postchecks, rollback conditions and procedure, non-rollbackable operations, hashes, expiry, and any separate critical warning. It accepts the exact owner phrase, requests execution, and displays safe results.

The GUI does not construct commands, assign risk, calculate hashes, read or store credentials, generate approval text, approve automatically, schedule work, execute business logic, or enable live transports. It uses the local core API's in-memory CSRF token and one-time request nonces.
