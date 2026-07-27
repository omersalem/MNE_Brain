import os
import re

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mapping of platform / path hints to specific credential secrets
CRED_REPLACEMENTS = [
    (r'secret_ref\("MNE_FORTIGATE_READONLY_PASSWORD"\)', 'secret_ref("MNE_FORTIGATE_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_CISCO_READONLY_PASSWORD"\)', 'secret_ref("MNE_CISCO_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_FMC_READONLY_PASSWORD"\)', 'secret_ref("MNE_FMC_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_FTD_READONLY_PASSWORD"\)', 'secret_ref("MNE_FTD_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_F5_READONLY_PASSWORD"\)', 'secret_ref("MNE_F5_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_WINRM_READONLY_PASSWORD"\)', 'secret_ref("MNE_WINRM_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_VCENTER_READONLY_PASSWORD"\)', 'secret_ref("MNE_VCENTER_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_FUJITSU_READONLY_PASSWORD"\)', 'secret_ref("MNE_FUJITSU_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_DEVICE_READONLY_PASSWORD"\)', 'secret_ref("MNE_UBUNTU_READONLY_CREDENTIAL")'),
    (r'secret_ref\("MNE_READONLY_SECRET"\)', 'secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL")')
]

def sanitize_and_refactor_docs():
    docs_dir = os.path.join(VAULT_ROOT, "company_docs")
    for root, _, files in os.walk(docs_dir):
        for f in files:
            if f.endswith(".md"):
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                
                for pat, rep in CRED_REPLACEMENTS:
                    content = re.sub(pat, rep, content)

                with open(fp, "w", encoding="utf-8") as file:
                    file.write(content)

if __name__ == "__main__":
    sanitize_and_refactor_docs()
    print("Refactored company docs secret references.")
