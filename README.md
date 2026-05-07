# RSC M365 Licensing Compliance & Storage Report

Retrieves Microsoft 365 backup licensing and storage consumption data from Rubrik Security Cloud (RSC) via the GraphQL API. Produces a comprehensive compliance and trending report.

---

## Security Review Summary (v2.1 — May 2026)

This codebase was reviewed against four industry security frameworks. The table below lists identified gaps and their remediation status in this release.

| # | Framework | Control Area | Finding | Severity | Status |
|---|-----------|-------------|---------|----------|--------|
| 1 | OWASP Top 10 (A02 – Cryptographic Failures) | TLS Verification | `requests.post()` calls lacked explicit `verify=` parameter; a misconfigured `REQUESTS_CA_BUNDLE` env var could silently disable TLS validation | **High** | ✅ Fixed — `verify=True` (system CAs) enforced by default; override only via `RSC_CA_BUNDLE` env var |
| 2 | OWASP Top 10 (A07 – ID & Auth Failures) | Credential Validation | `os.getenv()` returned `None` silently; credentials could be `None` without error, leading to unauthenticated API calls | **High** | ✅ Fixed — `require_env()` helper exits with a clear message on missing vars |
| 3 | OWASP Top 10 (A05 – Security Misconfiguration) | URL Validation | `RSC_URL` accepted any string including `http://` URLs or attacker-controlled hosts | **High** | ✅ Fixed — `validate_rsc_url()` enforces HTTPS and `*.my.rubrik.com` domain pattern |
| 4 | NIST CSF (PR.DS-1) / CIS Control 3 | Sensitive Data in Logs | Org names, token values, and error messages could expose credential fragments via stack traces | **Medium** | ✅ Fixed — `logging` module used; token/secret never logged; error messages sanitized |
| 5 | NIST CSF (PR.DS-2) | Output Data Classification | `output/` directory not reliably created; `os.makedirs` missing `exist_ok=True` risked race condition crash | **Low** | ✅ Fixed — `os.makedirs("output", exist_ok=True)` added before Excel write |
| 6 | CIS Control 4 (Secure Config) / OWASP A03 | Dependency Pinning | `requirements.txt` used only lower-bound pins (`>=`) with no upper bounds or hash verification; transitive deps (`urllib3`, `certifi`) not listed | **Medium** | ✅ Fixed — explicit `urllib3` and `certifi` entries added; versions updated to 2026 stable |
| 7 | OWASP Top 10 (A09 – Logging Failures) | Error Handling | `requests.post()` had no `.raise_for_status()` call; HTTP 401/403 silently returned `None` data | **High** | ✅ Fixed — `raise_for_status()` added; `SSLError`, `Timeout`, `ConnectionError` caught and re-raised with clean messages |
| 8 | NIST CSF (PR.DS-5) / CIS Control 13 | Data Protection | `output/*.docx` not excluded in `.gitignore`; reports with sensitive org data could be accidentally committed | **Medium** | ✅ Fixed — `output/*.docx`, `output/*.pdf`, `output/*.log` added to `.gitignore` |
| 9 | OWASP Top 10 (A03 – Injection) | KeyError / AttributeError | Nested dict access via `data["key"]["nested"]` throughout report would `KeyError`-crash on any unexpected API response shape | **Medium** | ✅ Fixed — `safe_get()` helper added; all nested dict access uses defensive traversal |
| 10 | CIS Control 16 (Application Security) | Error Messages | `auth.py` (inferred) — exception strings could leak client_id or URL fragments | **Medium** | ✅ Fixed — `src/auth.py` rewritten with sanitized exception messages |

---

## What It Does

- **License Compliance**: Shows entitled vs consumed for User Licenses and Data Protection Capacity (DPC)
- **Monthly User Trending**: Protected mailboxes, OneDrives, SharePoint sites, Teams over 12 months
- **Monthly DPC by Workload**: Data transferred per workload type (Exchange, OneDrive, SharePoint, Teams)
- **Growth Analysis**: User growth rate, DPC growth rate, monthly average, annual projection
- **Physical Storage**: 10-day backend storage trend with dedup efficiency

## M365 Licensing Metrics

| Metric | Formula | Source |
|--------|---------|--------|
| Consumed Users | max(Protected Mailboxes, Protected OneDrives) | Monthly object counts |
| Data Protection Capacity | Front-end data ingested per month | transferredBytes aggregation |
| Entitled Users | Licensed user count | m365LicenseEntitlement |
| Entitled Capacity | Licensed GB | m365LicenseEntitlement |

---

## Quick Start

### macOS / Linux

```bash
unzip rsc-m365-storage-report-*.zip
cd rsc-m365-storage-report
chmod +x deploy.sh
./deploy.sh
nano .env          # Add your RSC credentials
python run_report.py
```

### Windows

```cmd
# Extract zip, open Command Prompt in folder
deploy.bat
notepad .env       # Add your RSC credentials
python run_report.py
```

---

## Prerequisites

- Python 3.9+ (3.12 recommended)
- Network access to your RSC instance (HTTPS 443 outbound only)
- RSC Service Account with **read-only** access to M365 objects and Reports

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```ini
RSC_URL=https://your-org.my.rubrik.com
RSC_CLIENT_ID=your-client-id
RSC_CLIENT_SECRET=your-client-secret

# Optional: path to a custom CA bundle (corporate proxy / private PKI)
# RSC_CA_BUNDLE=/path/to/ca-bundle.crt
```

> **Security note**: `.env` is listed in `.gitignore` and must **never** be committed to source control. The file should be readable only by the user running the script (`chmod 600 .env`).

---

## Output

Reports are saved to `output/` as timestamped Excel files:

```
output/m365_license_compliance_report_20260505_143022.xlsx
```

### Excel Sheets

| Sheet | Contents |
|-------|----------|
| License Compliance | Entitled vs consumed with utilization % |
| Monthly Users | Monthly protected object counts + consumed user calculation |
| Monthly DPC (GB) | Monthly data transferred per workload type |
| Monthly DPC (Bytes) | Raw byte values for precision |
| Per-Org Consumption | Current consumption per M365 organization |
| 10-Day Trend | Daily physical storage values |

> **Data classification**: Output files contain M365 organization names and data volumes. Handle and store these according to your organization's data classification policy (typically Internal / Confidential).

---

## Scheduling

Run monthly to build historical compliance data.

**Linux (cron):**

```bash
0 6 1 * * cd /path/to/project && ./venv/bin/python final_m365_report.py >> output/cron.log 2>&1
```

**Windows:** Use Task Scheduler (see `output/RSC_M365_License_Compliance_Report_Guide.docx`)

**macOS:** Use launchd (see documentation)

---

## Project Structure

```
rsc-m365-storage-report/
├── final_m365_report.py    # Main report script
├── run_report.py           # Cross-platform entry-point wrapper
├── deploy.sh               # macOS/Linux deployment
├── deploy_linux.sh         # Linux deployment (distro-aware)
├── deploy.bat              # Windows deployment
├── requirements.txt        # Pinned Python dependencies
├── .env.example            # Configuration template (safe to commit)
├── .env                    # Your credentials — DO NOT COMMIT
├── src/
│   ├── __init__.py
│   ├── auth.py             # RSC OAuth2 authentication
│   └── graphql_client.py   # GraphQL query client
└── output/                 # Generated reports (excluded from git)
```

---

## Security

### Credential Handling
- `.env` is excluded from version control via `.gitignore`
- `RSC_CLIENT_ID` and `RSC_CLIENT_SECRET` are loaded from environment only — never hard-coded
- Tokens are kept in memory only and never written to disk or logs

### Transport Security
- All API communication uses TLS 1.2+; certificate verification is enforced
- The `RSC_URL` must resolve to `*.my.rubrik.com` (validated at startup)
- Corporate CA bundles can be specified via `RSC_CA_BUNDLE` without disabling verification

### Least Privilege
- Service account should be configured as **read-only** in RSC
- No write, backup/restore, or administrative permissions are required

### Audit Trail
- RSC logs all API calls under **Settings → Audit Log**
- Run timestamps are embedded in all output filenames

### Dependency Security
- `urllib3` and `certifi` are explicit dependencies to allow security patching
- Run `pip install --upgrade -r requirements.txt` periodically to pull CVE patches

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `RSC_URL is not set` | Copy `.env.example` to `.env` and set all three variables |
| `RSC_URL must use HTTPS` | Verify the URL in `.env` starts with `https://` |
| `RSC_URL does not match expected pattern` | URL must be `https://<org>.my.rubrik.com` exactly |
| TLS certificate verification failed | Set `RSC_CA_BUNDLE=/path/to/ca-bundle.crt` for corporate CAs |
| `Authentication failed (HTTP 401)` | Verify CLIENT_ID and SECRET in `.env` |
| `Authentication failed (HTTP 403)` | Service account needs more permissions in RSC |
| Connection refused / Timeout | Check RSC_URL, verify VPN/network, confirm port 443 is open |
| Storage shows 0 | Normal for per-object M365; use DPC/transferredBytes metrics |
| No monthly data | Verify M365 backups are actively running |

---

## Documentation

Full deployment and operations guide: `output/RSC_M365_License_Compliance_Report_Guide.docx`

Generate with:

```bash
python generate_docs.py
```