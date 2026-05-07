Security Policy
Supported Versions
VersionSupported2.x (current)✅ Active1.x❌ No longer maintained
Reporting a Vulnerability
If you discover a security vulnerability in this project, please do not open a public GitHub issue. Public disclosure before a fix is available puts users at risk.
Instead, report it privately:
Email: [your-security-email@example.com]
Subject line: [SECURITY] rsc-m365-storage – <brief description>
Please include:

A description of the vulnerability and its potential impact
Steps to reproduce or a proof-of-concept (if safe to share)
The version or commit hash you tested against
Any suggested remediation, if you have one

You can expect an acknowledgment within 3 business days and a status update within 10 business days.
Scope
This policy covers security issues in this repository's code, including:

Credential handling (src/auth.py, .env loading)
TLS/HTTPS configuration and certificate validation
Output file data exposure (report contents, logs)
Dependency vulnerabilities in requirements.txt
Injection or path traversal in any user-controlled input

Out of scope:

Vulnerabilities in Rubrik Security Cloud (RSC) itself — report those directly to Rubrik Support
General Python or third-party library CVEs not specific to how this project uses them

Security Design Principles
This tool was built with the following security posture:
Credential protection

Credentials are loaded exclusively from a local .env file — never hard-coded
.env is excluded from version control via .gitignore
Tokens are kept in memory only and never written to disk or logs

Transport security

All RSC API communication uses HTTPS with TLS certificate verification enforced
RSC_URL is validated at startup to match https://*.my.rubrik.com
Corporate CA bundles can be specified via RSC_CA_BUNDLE without disabling verification

Least privilege

The RSC service account requires read-only access only
No write, backup/restore, or administrative permissions are needed or requested

Output data handling

Report files contain M365 organization names and data volumes
output/ files are excluded from git to prevent accidental commit of sensitive data
Treat generated reports as Internal / Confidential per your organization's data policy

Dependency Security
Keep dependencies current to pick up CVE patches:
bashpip install --upgrade -r requirements.txt
Key security-relevant packages to monitor:

requests — HTTP client
urllib3 — TLS backend
certifi — CA bundle

Acknowledgments
We appreciate responsible disclosure and will acknowledge reporters (with permission) in release notes.