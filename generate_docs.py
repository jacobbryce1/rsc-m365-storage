#!/usr/bin/env python3
"""
Generate documentation:
1. Word document (wiki-style deployment & operations guide)
2. Updated README.md
"""

import os
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Inches, Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    import subprocess
    print("Installing python-docx...")
    subprocess.run(["pip", "install", "python-docx"], check=True)
    from docx import Document
    from docx.shared import Inches, Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH


def add_code_block(doc, code):
    """Add a formatted code block."""
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(1)
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(code)
    run.font.name = "Courier New"
    run.font.size = Pt(9)
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F0F0F0")
    para.paragraph_format.element.get_or_add_pPr().append(shd)


def generate_word_doc():
    """Generate the Word document."""
    doc = Document()

    # Title
    title = doc.add_heading("RSC M365 Licensing Compliance & Storage Report", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Deployment, Operations & Interpretation Guide")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("Version 2.0 - " + datetime.now().strftime("%B %d, %Y")).font.size = Pt(11)

    doc.add_page_break()

    # TOC
    doc.add_heading("Table of Contents", level=1)
    toc = [
        "1. Overview & Purpose",
        "2. M365 Licensing Model in RSC",
        "3. Report Outputs & Interpretation",
        "4. Prerequisites",
        "5. Deployment - macOS",
        "6. Deployment - Linux",
        "7. Deployment - Windows",
        "8. Configuration",
        "9. Running the Report",
        "10. Scheduling (Automated Execution)",
        "11. Data Sources & API Details",
        "12. Troubleshooting",
        "13. Security Considerations",
        "14. Appendix: RSC GraphQL Queries Used",
    ]
    for item in toc:
        doc.add_paragraph(item, style="List Number")

    doc.add_page_break()

    # 1. Overview
    doc.add_heading("1. Overview & Purpose", level=1)
    doc.add_paragraph(
        "This tool retrieves Microsoft 365 backup licensing and storage consumption data "
        "from Rubrik Security Cloud (RSC) via the GraphQL API. It produces a comprehensive "
        "report that helps organizations:"
    )
    for b in [
        "Monitor license compliance (entitled vs consumed users and capacity)",
        "Track monthly growth in protected users and data volumes",
        "Break down consumption by M365 workload type (Exchange, OneDrive, SharePoint, Teams)",
        "Forecast future capacity needs based on historical trends",
        "Identify potential license overages before they occur",
    ]:
        doc.add_paragraph(b, style="List Bullet")

    doc.add_heading("Key Metrics Provided", level=2)
    table = doc.add_table(rows=6, cols=4)
    table.style = "Table Grid"
    for i, h in enumerate(["Metric", "Granularity", "History", "Use Case"]):
        table.rows[0].cells[i].text = h
    metrics = [
        ("License Compliance", "Account-wide", "Current", "Are we within entitlement?"),
        ("Consumed User Licenses", "Monthly x Type", "~12 months", "User license trending"),
        ("Data Protection Capacity", "Monthly x Type", "~12 months", "DPC/capacity growth"),
        ("Physical Storage", "Per Org", "10 days", "Backend storage efficiency"),
        ("Growth Projections", "Calculated", "Forward 12mo", "Capacity planning"),
    ]
    for i, (m, g, h, u) in enumerate(metrics, 1):
        table.rows[i].cells[0].text = m
        table.rows[i].cells[1].text = g
        table.rows[i].cells[2].text = h
        table.rows[i].cells[3].text = u

    doc.add_page_break()

    # 2. Licensing Model
    doc.add_heading("2. M365 Licensing Model in RSC", level=1)
    doc.add_paragraph(
        "Rubrik Security Cloud measures M365 protection licensing on two primary metrics:"
    )

    doc.add_heading("User Licenses (per-user, per-month)", level=2)
    doc.add_paragraph(
        "Priced as $ per user per month. Editions include M365 Foundation, Professional, "
        "and Enterprise (plus EDU variants), each with different feature sets."
    )
    doc.add_paragraph("How consumed users are calculated:")
    doc.add_paragraph(
        "Consumed Users = MAX(protected user mailboxes, protected shared mailboxes, protected OneDrives)",
        style="List Bullet"
    )
    doc.add_paragraph(
        "This report tracks mailbox and OneDrive counts monthly and computes the consumed "
        "user count using this formula."
    )

    doc.add_heading("Data Protection Capacity (DPC, per-GB per-month)", level=2)
    doc.add_paragraph(
        "Separate capacity SKUs priced as $ per GB per month. RSC tracks DPC as the total "
        "front-end GB of live M365 snapshot data protected across Exchange, OneDrive, "
        "SharePoint, and Teams."
    )
    doc.add_paragraph(
        "This report uses 'Data Transferred' (transferredBytes) as the DPC metric - "
        "this represents the cumulative front-end data ingested during backup operations "
        "per workload type per month, which directly corresponds to the protected data volume."
    )

    doc.add_heading("Compliance Status", level=2)
    table = doc.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Status"
    table.rows[0].cells[1].text = "Meaning"
    table.rows[1].cells[0].text = "OK"
    table.rows[1].cells[1].text = "Utilization <= 100% - within entitlement"
    table.rows[2].cells[0].text = "OVER"
    table.rows[2].cells[1].text = "Utilization > 100% - exceeds entitlement, action needed"
    table.rows[3].cells[0].text = "Unknown"
    table.rows[3].cells[1].text = "Entitlement data not available (check service account permissions)"

    doc.add_page_break()

    # 3. Report Outputs
    doc.add_heading("3. Report Outputs & Interpretation", level=1)

    doc.add_heading("Console Output Sections", level=2)
    sections = [
        ("Section 1: License Compliance",
         "Shows entitled vs consumed for both User Licenses and DPC at the account level, "
         "with utilization percentages and compliance status. Also breaks down consumption per org."),
        ("Section 2: Monthly Consumed User Licenses",
         "12-month table showing monthly counts of protected Mailboxes, OneDrives, SharePoint Sites, "
         "and Teams. The 'Consumed Users' column shows max(Mailboxes, OneDrives) which is the "
         "billable user count per Rubrik's licensing formula."),
        ("Section 3: Monthly DPC by Workload Type",
         "12-month table showing data transferred (in GB) per workload type. Columns: Exchange, "
         "OneDrive, SharePoint, Teams, and Total. This represents the monthly data protection "
         "capacity consumption."),
        ("Section 4: Growth Analysis",
         "Calculates user growth rate, DPC growth rate, average monthly growth, and projected "
         "annual capacity. Use this for license renewal planning."),
        ("Section 5: Physical Storage Trend",
         "10-day trend of actual backend physical storage consumed across all M365 orgs. "
         "Shows the post-dedup/compression storage footprint."),
    ]
    for sect_title, desc in sections:
        doc.add_heading(sect_title, level=3)
        doc.add_paragraph(desc)

    doc.add_heading("Excel Export Sheets", level=2)
    table = doc.add_table(rows=7, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Sheet Name"
    table.rows[0].cells[1].text = "Contents"
    sheets = [
        ("License Compliance", "Entitled vs consumed summary with utilization %"),
        ("Monthly Users", "Monthly protected object counts and consumed user calculation"),
        ("Monthly DPC (GB)", "Monthly data transferred per workload type in GB"),
        ("Monthly DPC (Bytes)", "Same data in raw bytes for precision calculations"),
        ("Per-Org Consumption", "Current consumption broken down by M365 organization"),
        ("10-Day Trend", "Daily physical storage values for the last 10 days"),
    ]
    for i, (name, desc) in enumerate(sheets, 1):
        table.rows[i].cells[0].text = name
        table.rows[i].cells[1].text = desc

    doc.add_page_break()

    # 4. Prerequisites
    doc.add_heading("4. Prerequisites", level=1)

    doc.add_heading("Software", level=2)
    table = doc.add_table(rows=4, cols=3)
    table.style = "Table Grid"
    for i, h in enumerate(["Component", "Version", "Notes"]):
        table.rows[0].cells[i].text = h
    prereqs = [
        ("Python", "3.8+", "3.9+ recommended; 3.12+ ideal"),
        ("pip", "Latest", "Included with Python"),
        ("Network", "HTTPS 443", "Outbound to *.my.rubrik.com"),
    ]
    for i, (c, v, n) in enumerate(prereqs, 1):
        table.rows[i].cells[0].text = c
        table.rows[i].cells[1].text = v
        table.rows[i].cells[2].text = n

    doc.add_heading("RSC Service Account Requirements", level=2)
    doc.add_paragraph("Create a service account in RSC with the following permissions:")
    for p in [
        "Read access to M365 organizations and objects",
        "Read access to Reports and Compliance data",
        "View license entitlement information",
    ]:
        doc.add_paragraph(p, style="List Bullet")

    doc.add_heading("Creating the Service Account", level=3)
    for i, s in enumerate([
        "Log into RSC at https://YOUR_ORG.my.rubrik.com",
        "Navigate to Settings -> Service Accounts",
        "Click 'Create Service Account'",
        "Name: 'm365-reporting' (or similar descriptive name)",
        "Assign role: Read-only access to M365 and Reports",
        "Copy the Client ID and Client Secret immediately (shown only once)",
        "Store credentials securely",
    ], 1):
        doc.add_paragraph(str(i) + ". " + s)

    doc.add_page_break()

    # 5. macOS
    doc.add_heading("5. Deployment - macOS", level=1)

    doc.add_heading("Quick Start", level=2)
    add_code_block(doc, "# Extract the package\n"
        "unzip rsc-m365-storage-report-YYYYMMDD.zip\n"
        "cd rsc-m365-storage-report\n\n"
        "# Deploy (creates venv, installs dependencies)\n"
        "chmod +x deploy.sh\n"
        "./deploy.sh\n\n"
        "# Configure credentials\n"
        "nano .env\n\n"
        "# Run the report\n"
        "python run_report.py")

    doc.add_heading("Step 1: Verify Python", level=3)
    add_code_block(doc, "python3 --version\n# Must be 3.8 or higher\n# If not installed: brew install python3")

    doc.add_heading("Step 2: Extract & Deploy", level=3)
    doc.add_paragraph(
        "The deploy.sh script automatically creates a Python virtual environment, "
        "installs all dependencies, and creates a .env file from the template."
    )

    doc.add_heading("Step 3: Configure", level=3)
    add_code_block(doc, "# Edit .env with your RSC credentials:\n"
        "RSC_URL=https://your-org.my.rubrik.com\n"
        "RSC_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"
        "RSC_CLIENT_SECRET=your-secret-here")

    doc.add_heading("Step 4: Run", level=3)
    add_code_block(doc, "python run_report.py\n# Report appears on screen and saves to output/ directory")

    doc.add_paragraph(
        "Note: The LibreSSL warning on older macOS versions is cosmetic and does not affect functionality."
    )

    doc.add_page_break()

    # 6. Linux
    doc.add_heading("6. Deployment - Linux", level=1)

    doc.add_heading("Supported Distributions", level=2)
    for d in ["Ubuntu 20.04+", "Debian 11+", "RHEL / Rocky / Alma 8+", "Fedora 36+", "CentOS Stream 8+"]:
        doc.add_paragraph(d, style="List Bullet")

    doc.add_heading("Quick Start", level=2)
    add_code_block(doc, "unzip rsc-m365-storage-report-YYYYMMDD.zip\n"
        "cd rsc-m365-storage-report\n"
        "chmod +x deploy_linux.sh\n"
        "./deploy_linux.sh")

    doc.add_paragraph(
        "The Linux deployment script auto-detects your distribution and installs "
        "python3-venv and python3-pip if needed (requires sudo for package installation)."
    )

    doc.add_heading("Configure & Run", level=2)
    add_code_block(doc, "nano .env    # Add RSC credentials\npython run_report.py")

    doc.add_heading("Monthly Cron Job", level=2)
    add_code_block(doc, "crontab -e\n# Add this line (runs 1st of each month at 6 AM):\n"
        "0 6 1 * * cd /path/to/rsc-m365-storage-report && "
        "./venv/bin/python final_m365_report.py >> output/cron.log 2>&1")

    doc.add_page_break()

    # 7. Windows
    doc.add_heading("7. Deployment - Windows", level=1)

    doc.add_heading("Step 1: Install Python", level=2)
    doc.add_paragraph(
        "Download Python 3.9+ from https://www.python.org/downloads/windows/. "
        "IMPORTANT: During installation, check the box 'Add Python to PATH'."
    )

    doc.add_heading("Step 2: Extract & Deploy", level=2)
    add_code_block(doc, "# Extract zip via Windows Explorer (right-click -> Extract All)\n"
        "# Open Command Prompt in the extracted folder:\n"
        "cd rsc-m365-storage-report\n"
        "deploy.bat")

    doc.add_heading("Step 3: Configure", level=2)
    add_code_block(doc, "notepad .env\n# Set RSC_URL, RSC_CLIENT_ID, RSC_CLIENT_SECRET")

    doc.add_heading("Step 4: Run", level=2)
    add_code_block(doc, "python run_report.py")

    doc.add_heading("Task Scheduler (Monthly Automation)", level=2)
    for s in [
        "Open Task Scheduler (Win+R then taskschd.msc)",
        "Create Basic Task -> Name: 'RSC M365 License Report'",
        "Trigger: Monthly, Day 1, 6:00 AM",
        "Action: Start a Program",
        "Program: C:\\path\\to\\venv\\Scripts\\python.exe",
        "Arguments: final_m365_report.py",
        "Start in: C:\\path\\to\\rsc-m365-storage-report",
    ]:
        doc.add_paragraph(s, style="List Number")

    doc.add_page_break()

    # 8. Configuration
    doc.add_heading("8. Configuration", level=1)

    doc.add_heading("Environment Variables (.env file)", level=2)
    table = doc.add_table(rows=4, cols=4)
    table.style = "Table Grid"
    for i, h in enumerate(["Variable", "Required", "Format", "Description"]):
        table.rows[0].cells[i].text = h
    for i, (v, r, f, d) in enumerate([
        ("RSC_URL", "Yes", "https://org.my.rubrik.com", "RSC instance URL (no trailing slash)"),
        ("RSC_CLIENT_ID", "Yes", "UUID", "Service account client ID"),
        ("RSC_CLIENT_SECRET", "Yes", "String", "Service account secret"),
    ], 1):
        table.rows[i].cells[0].text = v
        table.rows[i].cells[1].text = r
        table.rows[i].cells[2].text = f
        table.rows[i].cells[3].text = d

    doc.add_heading("File Permissions", level=3)
    add_code_block(doc, "# macOS/Linux:\nchmod 600 .env\n\n"
        "# Windows: Right-click -> Properties -> Security -> restrict to your user")

    doc.add_page_break()

    # 9. Running
    doc.add_heading("9. Running the Report", level=1)

    doc.add_heading("Standard Execution", level=2)
    add_code_block(doc, "python run_report.py")

    doc.add_heading("Expected Runtime", level=2)
    doc.add_paragraph("30-60 seconds depending on network latency to RSC.")

    doc.add_heading("Output Location", level=2)
    add_code_block(doc, "output/m365_license_compliance_report_20260505_143022.xlsx")

    doc.add_heading("Manual Execution", level=2)
    add_code_block(doc, "# Activate virtual environment\n"
        "source venv/bin/activate    # macOS/Linux\n"
        "venv\\Scripts\\activate.bat   # Windows\n\n"
        "# Run directly\n"
        "python final_m365_report.py")

    doc.add_page_break()

    # 10. Scheduling
    doc.add_heading("10. Scheduling (Automated Execution)", level=1)
    doc.add_paragraph(
        "For continuous compliance monitoring, schedule monthly execution. "
        "Each run produces a timestamped report file, building a historical archive."
    )

    doc.add_heading("macOS (launchd)", level=2)
    add_code_block(doc,
        "# Create ~/Library/LaunchAgents/com.rsc.m365report.plist\n"
        "# Key settings:\n"
        "#   ProgramArguments: /path/to/venv/bin/python final_m365_report.py\n"
        "#   WorkingDirectory: /path/to/rsc-m365-storage-report\n"
        "#   StartCalendarInterval: Day=1, Hour=6\n\n"
        "launchctl load ~/Library/LaunchAgents/com.rsc.m365report.plist")

    doc.add_heading("Linux (cron)", level=2)
    add_code_block(doc, "0 6 1 * * cd /opt/rsc-m365-storage-report && "
        "./venv/bin/python final_m365_report.py >> output/cron.log 2>&1")

    doc.add_heading("Windows", level=2)
    doc.add_paragraph("See Section 7 for Task Scheduler setup.")

    doc.add_page_break()

    # 11. Data Sources
    doc.add_heading("11. Data Sources & API Details", level=1)

    doc.add_heading("RSC GraphQL Queries Used", level=2)
    table = doc.add_table(rows=6, cols=3)
    table.style = "Table Grid"
    for i, h in enumerate(["Query", "Returns", "Licensing Metric"]):
        table.rows[0].cells[i].text = h
    for i, (q, r, m) in enumerate([
        ("m365LicenseEntitlement", "usersEntitled, capacityEntitledInBytes", "Entitled (what you pay for)"),
        ("o365Consumption", "usersProtected, fetbConsumed per org", "Current consumed (point-in-time)"),
        ("snappableGroupByConnection", "Monthly counts + transferredBytes", "Historical consumed (12 mo)"),
        ("o365StorageStats", "Physical/logical, 10-day trend", "Backend storage efficiency"),
        ("o365Orgs", "M365 organization list", "Org enumeration"),
    ], 1):
        table.rows[i].cells[0].text = q
        table.rows[i].cells[1].text = r
        table.rows[i].cells[2].text = m

    doc.add_heading("Consumed User License Calculation", level=2)
    add_code_block(doc, "Consumed Users = MAX(O365Mailbox count, O365Onedrive count)\n\n"
        "Source: snappableGroupByConnection grouped by Month -> ObjectType\n"
        "  O365Mailbox count = protected mailboxes\n"
        "  O365Onedrive count = protected OneDrives")

    doc.add_heading("DPC Calculation", level=2)
    add_code_block(doc, "DPC = transferredBytes (cumulative data ingested per month)\n\n"
        "Source: snappableGroupByConnection -> aggregation.transferredBytes\n"
        "  Broken down by: Exchange, OneDrive, SharePoint, Teams\n"
        "  Reported in GB per month")

    doc.add_page_break()

    # 12. Troubleshooting
    doc.add_heading("12. Troubleshooting", level=1)
    for issue, fix in [
        ("Connection Refused / Timeout",
         "Verify RSC_URL in .env. Check VPN/network. Ensure HTTPS 443 is open outbound."),
        ("401 Unauthorized",
         "Check RSC_CLIENT_ID and RSC_CLIENT_SECRET. Verify service account is not expired."),
        ("403 Forbidden",
         "Service account lacks permissions. Add read access for M365 objects and Reports."),
        ("License Entitlement Shows N/A",
         "m365LicenseEntitlement may require elevated permissions. Contact RSC admin."),
        ("All Storage Values Show 0",
         "Normal for per-object M365. RSC tracks M365 at org aggregate level. Use DPC/transferredBytes."),
        ("LibreSSL Warning (macOS)",
         "Cosmetic only. To suppress: brew install python@3.12 and recreate venv."),
        ("Empty consumptionPerWorkloadType",
         "Some environments don't populate this. Monthly transferredBytes by type provides same data."),
        ("No Monthly Data",
         "Verify M365 backups are actively running. Data only appears from backup start date."),
        ("Python Not Found (Windows)",
         "Re-install Python with 'Add to PATH' checked. Or use full path to python.exe."),
    ]:
        doc.add_heading(issue, level=2)
        doc.add_paragraph(fix)

    doc.add_page_break()

    # 13. Security
    doc.add_heading("13. Security Considerations", level=1)
    for sec_title, desc in [
        ("Credential Protection",
         "The .env file contains sensitive RSC credentials. Never commit to version control. "
         "Set file permissions to 600. Consider a secrets manager for production."),
        ("Network Security",
         "All communication uses TLS 1.2+ over HTTPS. No plaintext credentials on the wire. "
         "OAuth2 tokens are short-lived and memory-only."),
        ("Service Account Scope",
         "Use minimum required permissions (read-only). No write, backup/restore, or admin needed."),
        ("Output Data Classification",
         "Reports contain org names, user counts, data volumes. Classify as internal/confidential."),
        ("Audit Trail",
         "RSC logs all API calls. Service account activity visible in Settings -> Audit Log."),
    ]:
        doc.add_heading(sec_title, level=2)
        doc.add_paragraph(desc)

    doc.add_page_break()

    # 14. Appendix
    doc.add_heading("14. Appendix: RSC GraphQL Queries Used", level=1)

    doc.add_heading("License Entitlement", level=2)
    add_code_block(doc, "{\n  m365LicenseEntitlement {\n"
        "    usersEntitled\n    capacityEntitledInBytes\n  }\n}")

    doc.add_heading("Per-Org Consumption", level=2)
    add_code_block(doc, 'query($input: O365ConsumptionInput!) {\n'
        '  o365Consumption(input: $input) {\n'
        '    consumption {\n'
        '      usersProtected\n'
        '      fetbConsumed\n'
        '    }\n'
        '    consumptionPerWorkloadType {\n'
        '      workloadType\n'
        '      consumption { usersProtected fetbConsumed }\n'
        '    }\n'
        '  }\n'
        '}\n'
        '# Variable: {"input": {"o365OrgId": "<org-uuid>"}}')

    doc.add_heading("Monthly Licensing Data (Core Query)", level=2)
    add_code_block(doc, '{\n'
        '  snappableGroupByConnection(\n'
        '    first: 24\n'
        '    groupBy: Month\n'
        '    filter: {\n'
        '      objectType: [O365Mailbox, O365Onedrive, O365Site, O365Teams]\n'
        '    }\n'
        '    requestedAggregations: [TRANSFERRED_BYTES, Count]\n'
        '  ) {\n'
        '    edges {\n'
        '      node {\n'
        '        groupByInfo {\n'
        '          ... on TimeRangeWithUnit { start end }\n'
        '        }\n'
        '        snappableConnection {\n'
        '          count\n'
        '          aggregation { transferredBytes }\n'
        '        }\n'
        '        snappableGroupBy(groupBy: ObjectType) {\n'
        '          groupByInfo {\n'
        '            ... on ObjectType { enumValue }\n'
        '          }\n'
        '          snappableConnection {\n'
        '            count\n'
        '            aggregation { transferredBytes }\n'
        '          }\n'
        '        }\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '}')

    doc.add_heading("Storage Statistics", level=2)
    add_code_block(doc, 'query($orgID: UUID) {\n'
        '  o365StorageStats(orgID: $orgID) {\n'
        '    liveDataSizeInBytes\n'
        '    physicalDataSizeInBytes\n'
        '    storageEfficiencyPercent\n'
        '    dailyGrowthInBytes\n'
        '    estimatedThirtyDaysStorageInBytes\n'
        '    physicalDataSizeTimeSeries {\n'
        '      physicalDataSizeInBytes\n'
        '      timestamp\n'
        '    }\n'
        '  }\n'
        '}')

    # Save
    os.makedirs("output", exist_ok=True)
    doc_path = "output/RSC_M365_License_Compliance_Report_Guide.docx"
    doc.save(doc_path)
    return doc_path


def generate_readme():
    """Generate updated README.md."""
    lines = []
    lines.append("# RSC M365 Licensing Compliance & Storage Report")
    lines.append("")
    lines.append("Retrieves Microsoft 365 backup licensing and storage consumption data from Rubrik Security Cloud (RSC) via the GraphQL API. Produces a comprehensive compliance and trending report.")
    lines.append("")
    lines.append("## What It Does")
    lines.append("")
    lines.append("- **License Compliance**: Shows entitled vs consumed for User Licenses and Data Protection Capacity (DPC)")
    lines.append("- **Monthly User Trending**: Protected mailboxes, OneDrives, SharePoint sites, Teams over 12 months")
    lines.append("- **Monthly DPC by Workload**: Data transferred per workload type (Exchange, OneDrive, SharePoint, Teams)")
    lines.append("- **Growth Analysis**: User growth rate, DPC growth rate, monthly average, annual projection")
    lines.append("- **Physical Storage**: 10-day backend storage trend with dedup efficiency")
    lines.append("")
    lines.append("## M365 Licensing Metrics")
    lines.append("")
    lines.append("| Metric | Formula | Source |")
    lines.append("|--------|---------|--------|")
    lines.append("| Consumed Users | max(Protected Mailboxes, Protected OneDrives) | Monthly object counts |")
    lines.append("| Data Protection Capacity | Front-end data ingested per month | transferredBytes aggregation |")
    lines.append("| Entitled Users | Licensed user count | m365LicenseEntitlement |")
    lines.append("| Entitled Capacity | Licensed GB | m365LicenseEntitlement |")
    lines.append("")
    lines.append("## Quick Start")
    lines.append("")
    lines.append("### macOS / Linux")
    lines.append("```bash")
    lines.append("unzip rsc-m365-storage-report-*.zip")
    lines.append("cd rsc-m365-storage-report")
    lines.append("chmod +x deploy.sh")
    lines.append("./deploy.sh")
    lines.append("nano .env          # Add your RSC credentials")
    lines.append("python run_report.py")
    lines.append("```")
    lines.append("")
    lines.append("### Windows")
    lines.append("```cmd")
    lines.append("# Extract zip, open Command Prompt in folder")
    lines.append("deploy.bat")
    lines.append("notepad .env       # Add your RSC credentials")
    lines.append("python run_report.py")
    lines.append("```")
    lines.append("")
    lines.append("## Prerequisites")
    lines.append("")
    lines.append("- Python 3.8+ (3.9+ recommended)")
    lines.append("- Network access to your RSC instance (HTTPS 443)")
    lines.append("- RSC Service Account with read access to M365 objects and Reports")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append("Copy `.env.example` to `.env` and set:")
    lines.append("")
    lines.append("```")
    lines.append("RSC_URL=https://your-org.my.rubrik.com")
    lines.append("RSC_CLIENT_ID=your-client-id")
    lines.append("RSC_CLIENT_SECRET=your-client-secret")
    lines.append("```")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    lines.append("Reports are saved to `output/` as timestamped Excel files:")
    lines.append("")
    lines.append("```")
    lines.append("output/m365_license_compliance_report_20260505_143022.xlsx")
    lines.append("```")
    lines.append("")
    lines.append("### Excel Sheets")
    lines.append("")
    lines.append("| Sheet | Contents |")
    lines.append("|-------|----------|")
    lines.append("| License Compliance | Entitled vs consumed with utilization % |")
    lines.append("| Monthly Users | Monthly protected object counts + consumed user calculation |")
    lines.append("| Monthly DPC (GB) | Monthly data transferred per workload type |")
    lines.append("| Monthly DPC (Bytes) | Raw byte values for precision |")
    lines.append("| Per-Org Consumption | Current consumption per M365 organization |")
    lines.append("| 10-Day Trend | Daily physical storage values |")
    lines.append("")
    lines.append("## Scheduling")
    lines.append("")
    lines.append("Run monthly to build historical compliance data:")
    lines.append("")
    lines.append("**Linux (cron):**")
    lines.append("```bash")
    lines.append("0 6 1 * * cd /path/to/project && ./venv/bin/python final_m365_report.py")
    lines.append("```")
    lines.append("")
    lines.append("**Windows:** Use Task Scheduler (see documentation)")
    lines.append("")
    lines.append("**macOS:** Use launchd (see documentation)")
    lines.append("")
    lines.append("## Project Structure")
    lines.append("")
    lines.append("```")
    lines.append("rsc-m365-storage-report/")
    lines.append("├── final_m365_report.py    # Main report script")
    lines.append("├── run_report.py           # Cross-platform wrapper")
    lines.append("├── deploy.sh               # macOS deployment")
    lines.append("├── deploy_linux.sh         # Linux deployment")
    lines.append("├── deploy.bat              # Windows deployment")
    lines.append("├── requirements.txt        # Python dependencies")
    lines.append("├── .env.example            # Configuration template")
    lines.append("├── .env                    # Your credentials (DO NOT COMMIT)")
    lines.append("├── src/")
    lines.append("│   ├── __init__.py")
    lines.append("│   ├── auth.py             # RSC OAuth2 authentication")
    lines.append("│   └── graphql_client.py   # GraphQL query client")
    lines.append("└── output/                 # Generated reports")
    lines.append("```")
    lines.append("")
    lines.append("## Security")
    lines.append("")
    lines.append("- `.env` contains credentials - never commit to version control")
    lines.append("- All communication uses TLS/HTTPS")
    lines.append("- Service account should have minimum required (read-only) permissions")
    lines.append("- Output files contain org names and data volumes - handle per your data policy")
    lines.append("")
    lines.append("## Troubleshooting")
    lines.append("")
    lines.append("| Issue | Solution |")
    lines.append("|-------|----------|")
    lines.append("| Connection refused | Check RSC_URL, verify VPN/network |")
    lines.append("| 401 Unauthorized | Verify CLIENT_ID and SECRET |")
    lines.append("| 403 Forbidden | Service account needs more permissions |")
    lines.append("| Storage shows 0 | Normal for per-object M365; use DPC/transferredBytes |")
    lines.append("| No monthly data | Verify M365 backups are actively running |")
    lines.append("")
    lines.append("## Documentation")
    lines.append("")
    lines.append("Full deployment and operations guide:")
    lines.append("`output/RSC_M365_License_Compliance_Report_Guide.docx`")
    lines.append("")
    lines.append("Generate with: `python generate_docs.py`")
    lines.append("")

    readme_path = "README.md"
    with open(readme_path, "w") as f:
        f.write("\n".join(lines))
    return readme_path


def main():
    print("=" * 60)
    print("  Generating Documentation & README")
    print("=" * 60 + "\n")

    print("Generating Word document...")
    doc_path = generate_word_doc()
    print("  Done: " + doc_path + "\n")

    print("Generating README.md...")
    readme_path = generate_readme()
    print("  Done: " + readme_path + "\n")

    print("=" * 60)
    print("  All documentation generated!")
    print("  Word:   " + doc_path)
    print("  README: " + readme_path)
    print("=" * 60)


if __name__ == "__main__":
    main()
