# 📊 RSC M365 Licensing Compliance & Storage Report

Automated Microsoft 365 backup licensing compliance and storage consumption reporting via the Rubrik Security Cloud (RSC) GraphQL API. Designed for environments from single-org to multi-org M365 tenants managed through RSC.

> **Not affiliated with Rubrik.** This is an independent, community-built tool. See [Legal & Disclaimer](#legal--disclaimer) for details.

---

## Overview

This tool connects to your RSC instance, retrieves M365 backup licensing and storage data, and produces a comprehensive compliance and trending report — surfacing license overages, consumption trends, and growth projections as a timestamped Excel workbook with console summary output.

**v2.1** introduces a full security hardening pass reviewed against OWASP Top 10, NIST CSF 2.0, CIS Controls v8, and MITRE ATT&CK. See [Security](#security) for details.

---

## Features

| Feature | Details |
|---------|---------|
| 📋 **License compliance** | Entitled vs consumed for User Licenses and Data Protection Capacity (DPC) |
| 📅 **Monthly user trending** | Protected mailboxes, OneDrives, SharePoint sites, and Teams over 12 months |
| 💾 **DPC by workload type** | Data transferred per workload (Exchange, OneDrive, SharePoint, Teams) |
| 📈 **Growth analysis** | User growth rate, DPC growth rate, monthly average, annual projection |
| 🗄️ **Physical storage trend** | 10-day backend storage with dedup efficiency |
| 🏢 **Multi-org support** | Aggregates consumption across all M365 organizations in your RSC tenant |
| 📥 **Excel export** | Six-sheet timestamped `.xlsx` workbook saved to `output/` |
| 🔒 **TLS-verified API calls** | Configurable CA bundle; `verify=False` removed entirely |
| 🔑 **URL + credential validation** | RSC_URL validated against `*.my.rubrik.com` at startup; missing vars exit cleanly |

---

## M365 Licensing Metrics

| Metric | Formula | API Source |
|--------|---------|------------|
| Consumed Users | `max(Protected Mailboxes, Protected OneDrives)` | `snappableGroupByConnection` monthly counts |
| Data Protection Capacity | Front-end data ingested per month | `transferredBytes` aggregation |
| Entitled Users | Licensed user count | `m365LicenseEntitlement` |
| Entitled Capacity | Licensed GB | `m365LicenseEntitlement` |

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.9 or higher (3.12 recommended) |
| Network | HTTPS access to your RSC instance (port 443 outbound) |
| RSC Permissions | Service account with read access to M365 objects and Reports |
| Disk Space | ~50 MB |

> You must have a valid API key and an active Rubrik Security Cloud subscription. This tool does not bypass licensing or provide unauthorised access to any Rubrik features.

---

## Quick Start

### macOS / Linux

```bash
# Clone or download the repo
unzip rsc-m365-storage-report-*.zip
cd rsc-m365-storage-report

# Set up environment
chmod +x deploy.sh && ./deploy.sh

# Configure credentials
cp .env.example .env
nano .env   # Add your RSC credentials

# Run
python run_report.py
```

### Windows (Command Prompt)

```bat
REM Extract zip, open Command Prompt in folder
deploy.bat
copy .env.example .env
notepad .env   REM Add your RSC credentials
python run_report.py
```

Reports are written to `output/` as timestamped Excel files when the run completes.

---

## Configuration

### 1. Create your `.env` file

```bash
cp .env.example .env
```

```dotenv
# Required
RSC_URL=https://your-org.my.rubrik.com
RSC_CLIENT_ID=your-client-id
RSC_CLIENT_SECRET=your-client-secret

# Optional: custom CA bundle for corporate proxies / private PKI
# RSC_CA_BUNDLE=/path/to/ca-bundle.crt
```

> ⚠️ **Never commit `.env` to version control.** It is already listed in `.gitignore`. On macOS/Linux, restrict the file to your user only: `chmod 600 .env`

### 2. RSC Service Account Setup

1. Log into RSC → **Settings** → **Service Accounts**
2. Create a new service account
3. Assign **read-only** access to M365 objects and Reports *(principle of least privilege)*
4. Copy the Client ID and Secret — the secret is shown only once
5. Paste values into your `.env`

### 3. TLS Configuration

RSC API calls verify TLS against system CAs by default. Override with `RSC_CA_BUNDLE`:

```dotenv
RSC_CA_BUNDLE=true                  # Default — verify against system CAs
RSC_CA_BUNDLE=/path/to/bundle.pem   # Custom CA bundle for corporate PKI
```

> `verify=False` has been removed from this codebase entirely. TLS verification cannot be disabled.

---

## Full Configuration Reference

### Required

| Variable | Description |
|----------|-------------|
| `RSC_URL` | Base URL of your RSC tenant — must match `https://<org>.my.rubrik.com` |
| `RSC_CLIENT_ID` | RSC service account client ID |
| `RSC_CLIENT_SECRET` | RSC service account secret |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `RSC_CA_BUNDLE` | `true` | `true` (system CAs) or path to a `.pem` CA bundle |

---

## Output

### Excel Workbook

```
output/m365_license_compliance_report_20260505_143022.xlsx
```

| Sheet | Contents |
|-------|----------|
| License Compliance | Entitled vs consumed with utilization % and status |
| Monthly Users | Monthly protected object counts + consumed user calculation |
| Monthly DPC (GB) | Monthly data transferred per workload type |
| Monthly DPC (Bytes) | Raw byte values for precision calculations |
| Per-Org Consumption | Current consumption broken down per M365 organization |
| 10-Day Trend | Daily physical storage values for the last 10 days |

> ⚠️ Output files contain M365 organization names and data volumes. Treat as **Internal / Confidential** per your organization's data classification policy.

---

## Scheduling

Run monthly to build a historical compliance archive.

**Linux (cron):**

```bash
0 6 1 * * cd /path/to/project && ./venv/bin/python final_m365_report.py >> output/cron.log 2>&1
```

**Windows:** Use Task Scheduler — see the full operations guide at `output/RSC_M365_License_Compliance_Report_Guide.docx`

**macOS:** Use launchd — see the full operations guide

---

## Project Structure

```
rsc-m365-storage-report/
├── final_m365_report.py    # Main report script
├── run_report.py           # Cross-platform entry-point wrapper
├── generate_docs.py        # Word doc + README generator
├── package_project.py      # Distribution packager
├── deploy.sh               # macOS/Linux deployment
├── deploy_linux.sh         # Linux deployment (distro-aware)
├── deploy.bat              # Windows deployment
├── requirements.txt        # Pinned Python dependencies
├── .env.example            # Configuration template (safe to commit)
├── .env                    # Your credentials — DO NOT COMMIT
├── SECURITY.md             # Vulnerability reporting policy
├── src/
│   ├── __init__.py
│   ├── auth.py             # RSC OAuth2 authentication
│   └── graphql_client.py   # GraphQL query client
└── output/                 # Generated reports (excluded from git)
```

---

## Security

v2.1 was reviewed against **OWASP Top 10 (2021)**, **NIST CSF 2.0**, **CIS Controls v8**, and **MITRE ATT&CK for Enterprise**. The following hardening measures are in place.

### Credential Protection

- Credentials are loaded exclusively from `.env` — never hard-coded
- Tokens are kept in memory only and never written to disk or logs
- Exception messages are sanitized — `CLIENT_ID`, `CLIENT_SECRET`, and token values never appear in tracebacks
- Use a **dedicated read-only service account**. Rotate the secret periodically to limit blast radius.

### TLS Verification

- All RSC API calls verify TLS against system CAs. This cannot be disabled.
- `RSC_URL` is validated at startup against `https://*.my.rubrik.com` — plaintext URLs and unexpected hosts are rejected before any credentials are transmitted.
- Corporate CA bundles can be specified via `RSC_CA_BUNDLE` without weakening verification.

### Output File Security

Assessment output contains M365 organization names, user counts, and data volumes. Treat it as sensitive.

- `output/` is excluded from version control via `.gitignore`
- Output files contain no credentials or tokens — only aggregated licensing and storage metrics

### Dependency Auditing

Dependencies are pinned in `requirements.txt` including `urllib3` and `certifi` for TLS-layer patch tracking. Keep them current:

```bash
pip install --upgrade -r requirements.txt
```

### Security Review Summary (v2.1)

| # | Framework | Finding | Severity | Status |
|---|-----------|---------|----------|--------|
| 1 | OWASP A02 | `requests.post()` lacked explicit `verify=` — silent TLS bypass possible | High | ✅ Fixed |
| 2 | OWASP A07 | `os.getenv()` returned `None` silently — unauthenticated API calls possible | High | ✅ Fixed |
| 3 | OWASP A05 | `RSC_URL` accepted any scheme/host — credentials could be sent to wrong host | High | ✅ Fixed |
| 4 | OWASP A09 | No `raise_for_status()` — HTTP 401/403 silently returned `None` | High | ✅ Fixed |
| 5 | NIST PR.DS-1 | Exception tracebacks could expose credential fragments | Medium | ✅ Fixed |
| 6 | OWASP A03 | Nested `data["key"]` access crashed on unexpected API response shapes | Medium | ✅ Fixed |
| 7 | NIST PR.DS-5 | `output/*.docx`, `*.pdf`, `*.log` not excluded from `.gitignore` | Medium | ✅ Fixed |
| 8 | CIS Control 4 | `urllib3` and `certifi` absent from `requirements.txt`; versions stale | Medium | ✅ Fixed |
| 9 | NIST PR.DS-2 | `os.makedirs` missing `exist_ok=True` — crash if `output/` absent | Low | ✅ Fixed |
| 10 | CIS Control 16 | `os.path.join` not used — forward-slash path non-portable on Windows | Low | ✅ Fixed |

See [SECURITY.md](SECURITY.md) for the vulnerability reporting policy.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `RSC_URL is not set` | Copy `.env.example` to `.env` and set all three required variables |
| `RSC_URL must use HTTPS` | Verify the URL in `.env` starts with `https://` |
| `RSC_URL does not match expected pattern` | URL must be exactly `https://<org>.my.rubrik.com` |
| TLS certificate verification failed | Set `RSC_CA_BUNDLE=/path/to/ca-bundle.crt` for corporate CAs |
| `Authentication failed (HTTP 401)` | Verify `RSC_CLIENT_ID` and `RSC_CLIENT_SECRET` in `.env` |
| `Authentication failed (HTTP 403)` | Service account needs read access to M365 objects and Reports |
| Connection refused / Timeout | Check `RSC_URL`, confirm VPN/network, verify port 443 is open outbound |
| Storage shows 0 | Normal for per-object M365 — use DPC / `transferredBytes` metrics instead |
| No monthly data | Verify M365 backups are actively running in RSC |

---

## Documentation

Full deployment and operations guide: `output/RSC_M365_License_Compliance_Report_Guide.docx`

Generate with:

```bash
python generate_docs.py
```

---

## Legal & Disclaimer

This project is an **independent, open-source tool** and is **not affiliated with, authorized, maintained, sponsored, or endorsed by Rubrik, Inc.** in any way. All product and company names are the registered trademarks of their respective owners. The use of any trade name or trademark is for identification and reference purposes only.

This software is provided **"as-is," without warranty of any kind**. Use of this tool is at your own risk. The authors are not responsible for any data loss, API rate-limit overages, account suspensions, or security incidents resulting from the use of this software.

You must have a valid API key and an active subscription or license for Rubrik Security Cloud (RSC). This software does not bypass any licensing checks or provide unauthorised access to Rubrik features.

---

## License

[Apache 2.0](LICENSE)