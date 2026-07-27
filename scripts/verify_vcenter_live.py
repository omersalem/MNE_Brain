import os
import sys
import json
import time
import datetime
import paramiko
from dotenv import load_dotenv

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(VAULT_ROOT, ".env"))

EVIDENCE_DIR = os.path.join(VAULT_ROOT, "operations", "evidence")

host = os.getenv("MNE_VCENTER_HOST", "172.23.69.38")
username = os.getenv("MNE_VCENTER_USERNAME", "root")
password = os.getenv("MNE_VCENTER_PASSWORD", "Kh@fud$2021")

print(f"==========================================")
print(f"Executing Live vCenter Inspection: {host}:22")
print(f"User: '{username}'")
print(f"==========================================")

now_iso = datetime.datetime.now().isoformat()
os.makedirs(EVIDENCE_DIR, exist_ok=True)
evidence_id = f"live-vcenter-main-{int(datetime.datetime.now().timestamp())}"
raw_path = os.path.join(EVIDENCE_DIR, f"{evidence_id}-raw.txt")
json_path = os.path.join(EVIDENCE_DIR, f"compute-{evidence_id}.json")

raw_output = ""
status = "FAILED"
error_msg = ""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(host, port=22, username=username, password=password, timeout=10)
    channel = client.invoke_shell()
    time.sleep(1)
    init_out = channel.recv(4096).decode('utf-8', errors='ignore')
    raw_output += f"--- Initial Prompt ---\n{init_out}\n"

    # Switch to BASH shell
    channel.send("shell\n")
    time.sleep(1)
    bash_out = channel.recv(4096).decode('utf-8', errors='ignore')
    raw_output += f"--- BASH Switch ---\n{bash_out}\n"

    cmds = [
        "uptime",
        "df -h",
        "cat /etc/photon-release",
        "service-control --status"
    ]

    for c in cmds:
        channel.send(c + "\n")
        time.sleep(2)
        out = channel.recv(16384).decode('utf-8', errors='ignore')
        raw_output += f"\n--- Executing: {c} ---\n{out}\n"

    client.close()
    status = "UP"

except Exception as e:
    error_msg = str(e)
    raw_output += f"\n[ERROR] SSH Connection failed: {error_msg}\n"
    print(f"[FAILED] vCenter verification failed: {error_msg}")

with open(raw_path, "w", encoding="utf-8") as f:
    f.write(raw_output)

evidence_record = {
    "evidence_id": evidence_id,
    "target_entity": "vcenter-main",
    "fqdn": "vcenter.mne.gov.ps",
    "ip": host,
    "port": 22,
    "protocol": "SSH",
    "username": username,
    "timestamp": now_iso,
    "trust_tier": 5,
    "status": status,
    "error": error_msg,
    "raw_output_path": os.path.relpath(raw_path, VAULT_ROOT).replace("\\", "/")
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(evidence_record, f, indent=2)

print(f"[OK] Saved vCenter live evidence ({status}) -> {json_path}")
