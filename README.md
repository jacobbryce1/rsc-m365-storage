# RSC M365 Licensing Compliance & Storage Report

Retrieves Microsoft 365 backup licensing and storage consumption data from Rubrik Security Cloud (RSC) via the GraphQL API. Produces a comprehensive compliance and trending report.

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

## Prerequisites

- Python 3.8+ (3.9+ recommended)
- Network access to your RSC instance (HTTPS 443)
- RSC Service Account with read access to M365 objects and Reports

## Configuration

Copy `.env.example` to `.env` and set:

```
RSC_URL=https://your-org.my.rubrik.com
RSC_CLIENT_ID=your-client-id
RSC_CLIENT_SECRET=your-client-secret
```

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

## Scheduling

Run monthly to build historical compliance data:

**Linux (cron):**
```bash
0 6 1 * * cd /path/to/project && ./venv/bin/python final_m365_report.py
```

**Windows:** Use Task Scheduler (see documentation)

**macOS:** Use launchd (see documentation)

## Project Structure

```
rsc-m365-storage-report/
├── final_m365_report.py    # Main report script
├── run_report.py           # Cross-platform wrapper
├── deploy.sh               # macOS deployment
├── deploy_linux.sh         # Linux deployment
├── deploy.bat              # Windows deployment
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template
├── .env                    # Your credentials (DO NOT COMMIT)
├── src/
│   ├── __init__.py
│   ├── auth.py             # RSC OAuth2 authentication
│   └── graphql_client.py   # GraphQL query client
└── output/                 # Generated reports
```

## Security

- `.env` contains credentials - never commit to version control
- All communication uses TLS/HTTPS
- Service account should have minimum required (read-only) permissions
- Output files contain org names and data volumes - handle per your data policy

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check RSC_URL, verify VPN/network |
| 401 Unauthorized | Verify CLIENT_ID and SECRET |
| 403 Forbidden | Service account needs more permissions |
| Storage shows 0 | Normal for per-object M365; use DPC/transferredBytes |
| No monthly data | Verify M365 backups are actively running |

## Documentation

Full deployment and operations guide:
`output/RSC_M365_License_Compliance_Report_Guide.docx`

Generate with: `python generate_docs.py`
