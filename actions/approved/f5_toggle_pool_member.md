# Action: F5 BIG-IP — Enable/Disable Pool Member

- **Action Name:** `f5_toggle_pool_member`
- **Target Platform:** F5 BIG-IP WAF
- **Risk Level:** Level 2 (Controlled Change)
- **Required Approval:** Operator Approval
- **Status:** REQUIRES APPROVAL

## 1. Pre-Checks
```bash
tmsh show ltm pool <POOL_NAME> members
```

## 2. Execution Commands (Disable for Maintenance)
```bash
tmsh modify ltm pool <POOL_NAME> members modify { <MEMBER_IP>:<PORT> { state user-down } }
```

## 3. Rollback Procedure (Enable)
```bash
tmsh modify ltm pool <POOL_NAME> members modify { <MEMBER_IP>:<PORT> { state user-up } }
```

## 4. Post-Validation
```bash
tmsh show ltm pool <POOL_NAME> members
```
