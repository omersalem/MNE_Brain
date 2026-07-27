import os
import sys
import json
import time
import telnetlib
import datetime
from dotenv import load_dotenv

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(VAULT_ROOT, ".env"))

EVIDENCE_DIR = os.path.join(VAULT_ROOT, "operations", "evidence")

BRANCHES = [
    {
        "id": "rtr-abudis-01",
        "name": "Abu Dis",
        "host_env": "MNE_ROUTER_ABUDIS_HOST",
        "default_host": "10.70.18.2",
        "user_env": "MNE_ROUTER_ABUDIS_USERNAME",
        "line_pw_env": "MNE_ROUTER_ABUDIS_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_ABUDIS_ENABLE_PASSWORD",
        "default_enable_pw": "deeso",
    },
    {
        "id": "rtr-bethlehem-01",
        "name": "Bethlehem",
        "host_env": "MNE_ROUTER_BETHLEHEM_HOST",
        "default_host": "10.60.18.2",
        "user_env": "MNE_ROUTER_BETHLEHEM_USERNAME",
        "line_pw_env": "MNE_ROUTER_BETHLEHEM_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_BETHLEHEM_ENABLE_PASSWORD",
        "default_enable_pw": "la7em",
    },
    {
        "id": "rtr-hebron-01",
        "name": "Hebron",
        "host_env": "MNE_ROUTER_HEBRON_HOST",
        "default_host": "10.40.18.2",
        "user_env": "MNE_ROUTER_HEBRON_USERNAME",
        "line_pw_env": "MNE_ROUTER_HEBRON_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_HEBRON_ENABLE_PASSWORD",
        "default_enable_pw": "5alelo",
    },
    {
        "id": "rtr-jenin-01",
        "name": "Jenin",
        "host_env": "MNE_ROUTER_JENIN_HOST",
        "default_host": "10.201.18.2",
        "user_env": "MNE_ROUTER_JENIN_USERNAME",
        "line_pw_env": "MNE_ROUTER_JENIN_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_JENIN_ENABLE_PASSWORD",
        "default_enable_pw": "jenina",
    },
    {
        "id": "rtr-jericho-01",
        "name": "Jericho",
        "host_env": "MNE_ROUTER_JERICHO_HOST",
        "default_host": "10.211.18.2",
        "user_env": "MNE_ROUTER_JERICHO_USERNAME",
        "line_pw_env": "MNE_ROUTER_JERICHO_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_JERICHO_ENABLE_PASSWORD",
        "default_enable_pw": "ree7o",
    },
    {
        "id": "rtr-nablus-01",
        "name": "Nablus",
        "host_env": "MNE_ROUTER_NABLUS_HOST",
        "default_host": "10.131.18.2",
        "user_env": "MNE_ROUTER_NABLUS_USERNAME",
        "line_pw_env": "MNE_ROUTER_NABLUS_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_NABLUS_ENABLE_PASSWORD",
        "default_enable_pw": "nabulsi",
    },
    {
        "id": "rtr-qalqilya-01",
        "name": "Qalqilya",
        "host_env": "MNE_ROUTER_QALQILYA_HOST",
        "default_host": "10.180.18.2",
        "user_env": "MNE_ROUTER_QALQILYA_USERNAME",
        "line_pw_env": "MNE_ROUTER_QALQILYA_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_QALQILYA_ENABLE_PASSWORD",
        "default_enable_pw": "qalqilo",
    },
    {
        "id": "rtr-salfit-01",
        "name": "Salfit",
        "host_env": "MNE_ROUTER_SALFIT_HOST",
        "default_host": "10.235.18.2",
        "user_env": "MNE_ROUTER_SALFIT_USERNAME",
        "line_pw_env": "MNE_ROUTER_SALFIT_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_SALFIT_ENABLE_PASSWORD",
        "default_enable_pw": "slfoo",
    },
    {
        "id": "rtr-tubas-01",
        "name": "Tubas",
        "host_env": "MNE_ROUTER_TUBAS_HOST",
        "default_host": "10.230.18.2",
        "user_env": "MNE_ROUTER_TUBAS_USERNAME",
        "line_pw_env": "MNE_ROUTER_TUBAS_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_TUBAS_ENABLE_PASSWORD",
        "default_enable_pw": "vivajaradatos",
    },
    {
        "id": "rtr-tulkarm-01",
        "name": "Tulkarm",
        "host_env": "MNE_ROUTER_TULKARM_HOST",
        "default_host": "10.165.18.2",
        "user_env": "MNE_ROUTER_TULKARM_USERNAME",
        "default_username": "noway",
        "line_pw_env": "MNE_ROUTER_TULKARM_LINE_PASSWORD",
        "default_line_pw": "vivajaradatos",
        "enable_pw_env": "MNE_ROUTER_TULKARM_ENABLE_PASSWORD",
        "default_enable_pw": "vivajaradatos",
    },
]

def verify_branch(b):
    host = os.getenv(b["host_env"], b["default_host"])
    username = os.getenv(b["user_env"], b.get("default_username", ""))
    line_pw = os.getenv(b["line_pw_env"], b["default_line_pw"])
    enable_pw = os.getenv(b["enable_pw_env"], b["default_enable_pw"])

    print(f"\n==========================================")
    print(f"Verifying Branch: {b['name']} ({b['id']}) at {host}:23")
    print(f"Auth: Username='{username}', LinePass='{line_pw}', EnablePass='{enable_pw}'")
    print(f"==========================================")

    now_iso = datetime.datetime.now().isoformat()
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    evidence_id = f"live-router-{b['id']}-{int(datetime.datetime.now().timestamp())}"
    raw_path = os.path.join(EVIDENCE_DIR, f"{evidence_id}-raw.txt")
    json_path = os.path.join(EVIDENCE_DIR, f"network-{evidence_id}.json")

    status = "FAILED"
    raw_output = ""
    error_msg = ""

    try:
        tn = telnetlib.Telnet(host, 23, timeout=10)
        time.sleep(1)
        initial = tn.read_very_eager().decode('ascii', errors='ignore')
        raw_output += f"--- Initial Prompt ---\n{initial}\n"

        if "Username:" in initial or "username:" in initial:
            tn.write(username.encode('ascii') + b"\n")
            time.sleep(1)
            after_user = tn.read_very_eager().decode('ascii', errors='ignore')
            raw_output += f"--- After Username ---\n{after_user}\n"

        tn.write(line_pw.encode('ascii') + b"\n")
        time.sleep(1)
        after_line = tn.read_very_eager().decode('ascii', errors='ignore')
        raw_output += f"--- After Line Password ---\n{after_line}\n"

        tn.write(b"enable\n")
        time.sleep(1)
        after_en_cmd = tn.read_very_eager().decode('ascii', errors='ignore')
        raw_output += f"--- After Enable Cmd ---\n{after_en_cmd}\n"

        if "Password:" in after_en_cmd or "password:" in after_en_cmd or "Password" in after_en_cmd:
            tn.write(enable_pw.encode('ascii') + b"\n")
            time.sleep(1)
            after_en_pw = tn.read_very_eager().decode('ascii', errors='ignore')
            raw_output += f"--- After Enable Password ---\n{after_en_pw}\n"

        tn.write(b"terminal length 0\n")
        time.sleep(0.5)

        tn.write(b"show version | include uptime|bytes of memory|processor\n")
        time.sleep(1.5)
        ver_out = tn.read_very_eager().decode('ascii', errors='ignore')
        raw_output += f"--- Show Version Output ---\n{ver_out}\n"

        tn.write(b"show ip interface brief\n")
        time.sleep(1.5)
        ip_out = tn.read_very_eager().decode('ascii', errors='ignore')
        raw_output += f"--- Show IP Int Brief ---\n{ip_out}\n"

        tn.write(b"exit\n")
        tn.close()
        status = "UP"

    except Exception as e:
        error_msg = str(e)
        raw_output += f"\n[ERROR] Connection failed: {error_msg}\n"
        print(f"[FAILED] Verification failed for {b['name']}: {error_msg}")

    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_output)

    evidence_record = {
        "evidence_id": evidence_id,
        "target_entity": b["id"],
        "branch": b["name"],
        "ip": host,
        "port": 23,
        "protocol": "Telnet",
        "auth_type": "username_line_enable" if username else "line_enable",
        "username": username,
        "line_pw_env": b["line_pw_env"],
        "enable_pw_env": b["enable_pw_env"],
        "timestamp": now_iso,
        "trust_tier": 5,
        "status": status,
        "error": error_msg,
        "raw_output_path": os.path.relpath(raw_path, VAULT_ROOT).replace("\\", "/")
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(evidence_record, f, indent=2)

    print(f"[OK] Saved evidence for {b['name']} ({status}) -> {json_path}")
    return evidence_record

def main():
    results = []
    for b in BRANCHES:
        res = verify_branch(b)
        results.append(res)
    
    print("\n==========================================")
    print("ALL BRANCH VERIFICATION SUMMARY")
    print("==========================================")
    for r in results:
        print(f" - {r['branch']} ({r['ip']}): {r['status']}")

if __name__ == "__main__":
    main()
